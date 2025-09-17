import os
import json
import requests
from time import time
import hmac
import hashlib
import urllib.parse # 引入這個函式庫來進行 URL 編碼

# --- 從 Railway 環境變數中讀取 API 資訊 ---
# 請確保您在 Railway 的 Variables 中設定了這些鍵值
API_KEY = os.environ.get('API_KEY')
API_SECRET = os.environ.get('API_SECRET')
SUB_ACCOUNT_EMAIL = os.environ.get('SUB_ACCOUNT_EMAIL')
SYMBOL = os.environ.get('SYMBOL', 'DOGEUSDC') # 預設 DOGEUSDC

# 幣安 API URL
BASE_FUTURES_URL = 'https://fapi.binance.com' # U本位合約
BASE_SAPI_URL = 'https://api.binance.com' # 子帳號管理

def sign_request(params: dict) -> str:
    """
    使用 HMAC SHA256 簽名方法：
    1. 將參數編碼 (URL Encode) 成標準的查詢字串。
    2. 進行 HMAC 簽名。
    """
    # 1. 對字典中的參數進行 URL 編碼，得到標準的 query string
    query_string = urllib.parse.urlencode(params) 
    
    # 2. 進行 HMAC SHA256 簽名
    signature = hmac.new(
        API_SECRET.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return signature

def fetch_api(url, params, headers):
    """ 統一的 API 請求發送函式，處理簽名和錯誤。 """
    
    # 1. 加入 timestamp
    params['timestamp'] = int(time() * 1000)
    
    # 2. 計算並加入簽名
    params['signature'] = sign_request(params)
    
    response = requests.get(
        url,
        headers=headers,
        params=params, # requests 函式庫會自動將參數組合成 URL
        timeout=15 
    )
    
    # 檢查並拋出 HTTP 錯誤 (這是解決 400, 401, 403 錯誤的關鍵)
    response.raise_for_status() 
    return response.json()

def get_leverage_bracket(symbol: str):
    """
    1. 呼叫 /fapi/v1/leverageBracket 取得槓桿分級表 (需要 API Key 和簽名)。
    """
    endpoint = '/fapi/v1/leverageBracket'
    url = BASE_FUTURES_URL + endpoint
    headers = {'X-MBX-APIKEY': API_KEY}
    params = {'symbol': symbol}
    
    data = fetch_api(url, params, headers)
    
    # 提取槓桿分級資訊並按名義價值由大到小排序
    brackets_info = data[0]['brackets']
    risk_levels = sorted([
        {'maxLeverage': b['initialLeverage'], 'maxNotionalValue': float(b['notionalCap'])}
        for b in brackets_info
    ], key=lambda x: x['maxNotionalValue'], reverse=True)
    
    return risk_levels

def get_sub_account_position_risk(email: str, symbol: str):
    """
    2. 呼叫 /sapi/v1/sub-account/futures/positionRisk 取得倉位資訊 (需要 SAPI 權限和簽名)。
    """
    endpoint = '/sapi/v1/sub-account/futures/positionRisk'
    url = BASE_SAPI_URL + endpoint
    headers = {'X-MBX-APIKEY': API_KEY}
    
    # futuresType=1 代表 USDT-Margined (U本位) 合約
    params = {'email': email, 'futuresType': 1}
    
    data = fetch_api(url, params, headers)
    
    # 找出目標交易對的倉位資訊
    doge_position = next((p for p in data if p['symbol'] == symbol), None)
    
    if doge_position:
        # 返回當前倉位的名義價值 (取絕對值)
        return abs(float(doge_position.get('notional', 0)))
    
    return 0.0

def main():
    if not all([API_KEY, API_SECRET, SUB_ACCOUNT_EMAIL]):
        print("錯誤：請檢查 Railway 環境變數是否設定完整 (API keys, email)。")
        return

    try:
        print("--- 正在透過 API 查詢幣安合約槓桿資訊 ---")
        
        # 1. 獲取風險限額分級表
        risk_levels = get_leverage_bracket(SYMBOL)
        
        # 2. 獲取子帳號當前倉位名義價值
        current_notional_value = get_sub_account_position_risk(SUB_ACCOUNT_EMAIL, SYMBOL)
        
        # 3. 判斷最大槓桿
        max_leverage = next((level['maxLeverage'] for level in risk_levels 
                             if current_notional_value <= level['maxNotionalValue']), 0)
        
        
        print("\n--- 幣安 U 本位合約最大槓桿查詢結果 ---")
        print(f"交易對: {SYMBOL}")
        print(f"子帳號 Email: {SUB_ACCOUNT_EMAIL}")
        print(f"當前倉位名義價值: {current_notional_value:.2f} USDC")
        
        if max_leverage > 0:
            print(f"**子帳號目前最大可設定槓桿倍數: {max_leverage} 倍**")
        else:
            print("倉位名義價值超過所有風險限額。")
            
    except requests.exceptions.HTTPError as e:
        # 捕獲所有 4xx 或 5xx 錯誤
        print(f"\n--- API 請求失敗 (HTTP Error {e.response.status_code}) ---")
        print(f"**幣安返回錯誤信息:** {e.response.text.strip()}")
        print("\n請務必檢查：")
        print("1. **API SECRET**：確保 Railway 環境變數中的 Secret Key **完全正確且無多餘空格**。")
        print("2. **API 權限**：確保主帳號 API Key 啟用了 **Enable Futures** 和 **Enable Sub Account** 權限。")
    except Exception as e:
        print(f"發生未知錯誤: {e}")

if __name__ == "__main__":
    main()
