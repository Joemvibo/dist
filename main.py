import os
import json
import requests
from time import time
import hmac
import hashlib

# --- 從 Railway 環境變數中讀取 API 資訊 ---
API_KEY = os.environ.get('API_KEY')
API_SECRET = os.environ.get('API_SECRET')
SUB_ACCOUNT_EMAIL = os.environ.get('SUB_ACCOUNT_EMAIL')
SYMBOL = os.environ.get('SYMBOL', 'DOGEUSDC') # 可在 Railway 變數中設定

# 幣安 API URL
BASE_FUTURES_URL = 'https://fapi.binance.com'
BASE_SAPI_URL = 'https://api.binance.com'

def sign_request(params: dict) -> str:
    """
    使用 HMAC SHA256 簽名方法。
    """
    query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
    signature = hmac.new(
        API_SECRET.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature

def get_leverage_bracket(symbol: str):
    """
    1. 呼叫 /fapi/v1/leverageBracket 取得該幣種的槓桿分級表 (需簽名)。
    """
    endpoint = '/fapi/v1/leverageBracket'
    timestamp = int(time() * 1000)
    
    params = {'symbol': symbol, 'timestamp': timestamp}
    params['signature'] = sign_request(params)
    
    response = requests.get(
        BASE_FUTURES_URL + endpoint,
        headers={'X-MBX-APIKEY': API_KEY},
        params=params
    )
    response.raise_for_status() # 檢查 HTTP 錯誤
    data = response.json()
    
    # 提取槓桿分級資訊並按名義價值由大到小排序
    brackets_info = data[0]['brackets']
    risk_levels = sorted([
        {'maxLeverage': b['initialLeverage'], 'maxNotionalValue': float(b['notionalCap'])}
        for b in brackets_info
    ], key=lambda x: x['maxNotionalValue'], reverse=True)
    
    return risk_levels

def get_sub_account_position_risk(email: str, symbol: str):
    """
    2. 呼叫 /sapi/v1/sub-account/futures/positionRisk 取得子帳號倉位資訊 (需簽名與 SAPI 權限)。
    """
    endpoint = '/sapi/v1/sub-account/futures/positionRisk'
    timestamp = int(time() * 1000)
    
    # futuresType=1 代表 USDT-Margined (U本位) 合約
    params = {'email': email, 'futuresType': 1, 'timestamp': timestamp}
    params['signature'] = sign_request(params)
    
    response = requests.get(
        BASE_SAPI_URL + endpoint,
        headers={'X-MBX-APIKEY': API_KEY},
        params=params
    )
    
    response.raise_for_status() # 檢查 HTTP 錯誤
    data = response.json()
    
    # 找出目標交易對的倉位資訊
    doge_position = next((p for p in data if p['symbol'] == symbol), None)
    
    if doge_position:
        # 返回當前倉位的名義價值 (取絕對值)
        return abs(float(doge_position.get('notional', 0)))
    
    return 0.0

def main():
    if not all([API_KEY, API_SECRET, SUB_ACCOUNT_EMAIL]):
        print("錯誤：請在 Railway 環境變數中設定 API 資訊。")
        return

    try:
        print("--- 正在查詢幣安合約槓桿資訊 ---")
        
        # 1. 獲取風險限額分級表
        risk_levels = get_leverage_bracket(SYMBOL)
        
        # 2. 獲取子帳號當前倉位名義價值
        current_notional_value = get_sub_account_position_risk(SUB_ACCOUNT_EMAIL, SYMBOL)
        
        max_leverage = 0
        
        # 3. 根據倉位價值，在分級表中找到最大可用槓桿
        for level in risk_levels:
            if current_notional_value <= level['maxNotionalValue']:
                max_leverage = level['maxLeverage']
                break
        
        print("\n--- 幣安 U 本位合約最大槓桿查詢結果 ---")
        print(f"交易對: {SYMBOL}")
        print(f"子帳號 Email: {SUB_ACCOUNT_EMAIL}")
        print(f"當前倉位名義價值: {current_notional_value:.2f} USDC")
        
        if max_leverage > 0:
            print(f"**子帳號目前最大可設定槓桿倍數: {max_leverage} 倍**")
        else:
            print("倉位名義價值超過所有風險限額。")
            
    except requests.exceptions.HTTPError as e:
        print(f"\n--- API 請求失敗 (HTTP Error) ---")
        print(f"HTTP 錯誤碼: {e.response.status_code}")
        print(f"幣安錯誤信息: {e.response.text}")
        print("請檢查 API Key 權限（Futures, Sub Account）和 IP 白名單是否設定正確。")
    except Exception as e:
        print(f"發生未知錯誤: {e}")

if __name__ == "__main__":
    main()
