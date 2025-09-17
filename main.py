import os
import json
import requests
from time import time
import hmac
import hashlib

# --- 【環境變數設定】---
# 程式會從 Railway 環境變數讀取這些值
API_KEY = os.environ.get('API_KEY')
API_SECRET = os.environ.get('API_SECRET')
SUB_ACCOUNT_EMAIL = os.environ.get('SUB_ACCOUNT_EMAIL')
SYMBOL = os.environ.get('SYMBOL', 'DOGEUSDC') 

# 幣安 API URL
BASE_FUTURES_URL = 'https://fapi.binance.com'
BASE_SAPI_URL = 'https://api.binance.com'

# --- 免費代理設定 ---
# 警告: 免費代理不穩定且有安全風險。這僅用於測試繞過連線限制。
# 您需要自行尋找並替換一個可用的代理 IP:PORT
PROXY_URL = os.environ.get('PROXY_URL', 'http://123.123.123.123:8080') # 請替換為您找到的代理IP:PORT

# 設置 requests 函式庫使用的代理
PROXIES = {
    'http': PROXY_URL,
    'https': PROXY_URL,
}
# --- 代理設定結束 ---


def sign_request(params: dict) -> str:
    """ 使用 HMAC SHA256 簽名。 """
    query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
    signature = hmac.new(
        API_SECRET.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature

def fetch_api(url, params, headers, use_proxy=False):
    """ 統一的 API 請求發送函式，可選擇是否使用代理。 """
    options = {
        'headers': headers,
        'params': params,
        'proxies': PROXIES if use_proxy else None, # 這裡使用代理
        'timeout': 10 # 設定超時時間，因為代理可能很慢
    }
    response = requests.get(url, **options)
    response.raise_for_status() 
    return response.json()


def get_leverage_bracket(symbol: str):
    """ 1. 呼叫 /fapi/v1/leverageBracket 取得槓桿分級表 (需簽名)。 """
    endpoint = '/fapi/v1/leverageBracket'
    timestamp = int(time() * 1000)
    
    params = {'symbol': symbol, 'timestamp': timestamp}
    params['signature'] = sign_request(params)
    
    url = BASE_FUTURES_URL + endpoint
    headers = {'X-MBX-APIKEY': API_KEY}
    
    return fetch_api(url, params, headers, use_proxy=True) # 使用代理


def get_sub_account_position_risk(email: str, symbol: str):
    """ 2. 呼叫 /sapi/v1/sub-account/futures/positionRisk 取得倉位資訊 (需簽名)。 """
    endpoint = '/sapi/v1/sub-account/futures/positionRisk'
    timestamp = int(time() * 1000)
    
    params = {'email': email, 'futuresType': 1, 'timestamp': timestamp}
    params['signature'] = sign_request(params)
    
    url = BASE_SAPI_URL + endpoint
    headers = {'X-MBX-APIKEY': API_KEY}
    
    data = fetch_api(url, params, headers, use_proxy=True) # 使用代理
    
    doge_position = next((p for p in data if p['symbol'] == symbol), None)
    return abs(float(doge_position.get('notional', 0))) if doge_position else 0.0


def main():
    if not all([API_KEY, API_SECRET, SUB_ACCOUNT_EMAIL, PROXY_URL]):
        print("錯誤：請檢查環境變數是否設定完整 (API keys, email, PROXY_URL)。")
        return

    try:
        print(f"--- 嘗試透過代理 {PROXY_URL} 查詢幣安合約槓桿資訊 ---")
        
        # 1. 獲取風險限額分級表
        brackets_data = get_leverage_bracket(SYMBOL)
        risk_levels = sorted([
            {'maxLeverage': b['initialLeverage'], 'maxNotionalValue': float(b['notionalCap'])}
            for b in brackets_data[0]['brackets']
        ], key=lambda x: x['maxNotionalValue'], reverse=True)
        
        # 2. 獲取子帳號當前倉位名義價值
        current_notional_value = get_sub_account_position_risk(SUB_ACCOUNT_EMAIL, SYMBOL)
        
        # 3. 判斷最大槓桿
        max_leverage = next((level['maxLeverage'] for level in risk_levels 
                             if current_notional_value <= level['maxNotionalValue']), 0)
        
        
        print("\n--- 幣安 U 本位合約最大槓桿查詢結果 ---")
        print(f"交易對: {SYMBOL}")
        print(f"當前倉位名義價值: {current_notional_value:.2f} USDC")
        print(f"**子帳號目前最大可設定槓桿倍數: {max_leverage} 倍**")
            
    except requests.exceptions.HTTPError as e:
        print(f"\n--- API 請求失敗 ---")
        print(f"HTTP 錯誤碼: {e.response.status_code}")
        print(f"幣安錯誤信息: {e.response.text.strip()}")
        print("可能原因：代理伺服器失效、代理被幣安封鎖或 API 權限錯誤。")
    except requests.exceptions.ProxyError as e:
        print(f"\n--- 代理連線錯誤 ---")
        print("請更換一個可用的免費代理 IP:PORT。")
    except Exception as e:
        print(f"發生未知錯誤: {e}")

if __name__ == "__main__":
    main()
