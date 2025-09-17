import os
import json
import requests
from time import time
import hmac
import hashlib
import urllib.parse
# --- 修正後的導入：使用通用的 Client ---
from binance.client import Client 
from binance.exceptions import BinanceAPIException
# ------------------------------------

# --- 【環境變數設定】---
API_KEY = os.environ.get('API_KEY')
API_SECRET = os.environ.get('API_SECRET')
SUB_ACCOUNT_EMAIL = os.environ.get('SUB_ACCOUNT_EMAIL')
SYMBOL = os.environ.get('SYMBOL', 'DOGEUSDC') 
TARGET_LEVERAGE = int(os.environ.get('TARGET_LEVERAGE', 20)) 

# 幣安 API URL (SAPI 不變，因為它是 REST API)
BASE_SAPI_URL = 'https://api.binance.com' 

# 創建通用的 Client 客戶端 (用於設定槓桿)
# 這個 Client 會自動處理 U 本位合約操作
client = Client(API_KEY, API_SECRET) 


def sign_request(params: dict) -> str:
    """
    用於 SAPI 請求的簽名邏輯 (未變動)。
    """
    query_string = urllib.parse.urlencode(params)
    signature = hmac.new(
        API_SECRET.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature

def fetch_sub_account_api(endpoint: str, params: dict):
    """
    處理 SAPI 請求的函式 (未變動)。
    """
    params['timestamp'] = int(time() * 1000)
    params['signature'] = sign_request(params)
    
    url = BASE_SAPI_URL + endpoint
    headers = {'X-MBX-APIKEY': API_KEY}
    
    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=15 
    )
    
    response.raise_for_status() 
    return response.json()


def get_sub_account_position_risk(email: str, symbol: str):
    """
    查詢子帳號的當前倉位名義價值 (邏輯未變動)。
    """
    endpoint = '/sapi/v1/sub-account/futures/positionRisk'
    params = {'email': email, 'futuresType': 1, 'symbol': symbol}
    
    data = fetch_sub_account_api(endpoint, params)
    
    doge_position = next((p for p in data if p.get('symbol') == symbol), None)
    
    if doge_position:
        return abs(float(doge_position.get('notional', 0)))
    
    return 0.0


def set_target_leverage(symbol: str, leverage: int):
    """
    設定特定交易對的槓桿倍數 (使用 Client 函式庫的方法)。
    """
    print(f"-> 正在嘗試設定 {symbol} 的槓桿為 {leverage} 倍...")
    
    try:
        # **關鍵變動：使用 client.futures_change_leverage()**
        result = client.futures_change_leverage(symbol=symbol, leverage=leverage)
        
        print("   ✅ 槓桿設定成功！")
        print(f"   設定結果: {result}")
        return True
    
    except BinanceAPIException as e:
        error_msg = str(e)
        print(f"   ❌ 設定失敗：幣安 API 錯誤: {error_msg}")
        return False
    except Exception as e:
        print(f"   ❌ 設定失敗，發生非 API 錯誤: {str(e)}")
        return False


def main():
    if not all([API_KEY, API_SECRET, SUB_ACCOUNT_EMAIL]):
        print("錯誤：請檢查 Railway 環境變數是否設定完整。")
        return

    print("--- 正在執行子帳號合約槓桿設置 ---")

    try:
        # 1. 查詢當前倉位名義價值 (驗證 SAPI 連線)
        current_notional_value = get_sub_account_position_risk(SUB_ACCOUNT_EMAIL, SYMBOL)
        
        print(f"交易對: {SYMBOL}")
        print(f"子帳號 Email: {SUB_ACCOUNT_EMAIL}")
        print(f"當前倉位名義價值: {current_notional_value:.2f} USDC")
        
        # 2. 執行槓桿設定
        set_target_leverage(SYMBOL, TARGET_LEVERAGE)
        
    except requests.exceptions.HTTPError as e:
        print(f"\n--- SAPI 查詢失敗 (HTTP Error {e.response.status_code}) ---")
        print(f"**幣安錯誤信息:** {e.response.text.strip()}")
        print("請檢查 API 權限。")
    except Exception as e:
        print(f"發生未知錯誤: {e}")

if __name__ == "__main__":
    main()
