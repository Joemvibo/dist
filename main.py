import os
import json
import requests
from time import time
import hmac
import hashlib
import urllib.parse
from binance.um_futures import UMFutures # 幣安 U 本位合約操作函式庫
from binance.lib.utils import config_logging # 用於錯誤日誌

# 啟用日誌記錄，便於在 Railway 中追蹤錯誤
config_logging(logging.INFO)

# --- 【環境變數設定】---
# 程式會從 Railway 環境變數讀取這些值
API_KEY = os.environ.get('API_KEY')
API_SECRET = os.environ.get('API_SECRET')
SUB_ACCOUNT_EMAIL = os.environ.get('SUB_ACCOUNT_EMAIL')
SYMBOL = os.environ.get('SYMBOL', 'DOGEUSDC') # 交易對
TARGET_LEVERAGE = int(os.environ.get('TARGET_LEVERAGE', 20)) # 您想要的槓桿倍數，預設 20

# 幣安 API URL
BASE_SAPI_URL = 'https://api.binance.com' # 子帳號管理

# 創建 UMFutures 客戶端 (用於設定槓桿)
# 這個客戶端會自動處理簽名和時間戳
futures_client = UMFutures(key=API_KEY, secret=API_SECRET)


def sign_request(params: dict) -> str:
    """
    用於 SAPI 請求的簽名邏輯。
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
    處理 SAPI 請求的函式 (用於查詢子帳號倉位風險)。
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
    查詢子帳號的當前倉位名義價值。
    """
    endpoint = '/sapi/v1/sub-account/futures/positionRisk'
    # futuresType=1 代表 USDT-Margined (U本位) 合約
    params = {'email': email, 'futuresType': 1, 'symbol': symbol}
    
    data = fetch_sub_account_api(endpoint, params)
    
    # 找出目標交易對的倉位資訊
    doge_position = next((p for p in data if p.get('symbol') == symbol), None)
    
    if doge_position:
        # 返回當前倉位的名義價值 (取絕對值)
        return abs(float(doge_position.get('notional', 0)))
    
    return 0.0


def set_target_leverage(symbol: str, leverage: int):
    """
    使用 UMFutures 客戶端設定特定交易對的槓桿倍數。
    """
    print(f"-> 正在嘗試設定 {symbol} 的槓桿為 {leverage} 倍...")
    
    try:
        # 這是 python-binance 函式庫提供的簡潔方法
        result = futures_client.change_leverage(symbol=symbol, leverage=leverage)
        
        print("   ✅ 槓桿設定成功！")
        print(f"   設定結果: {result}")
        return True
    
    except Exception as e:
        error_msg = str(e)
        
        if "leverage is too high" in error_msg:
             print(f"   ❌ 設定失敗：目標槓桿 {leverage} 超過 {symbol} 的最大允許槓桿。")
        elif "Invalid API-Key" in error_msg:
             print("   ❌ 設定失敗：API Key 或 Secret 錯誤。")
        else:
            print(f"   ❌ 設定失敗，發生錯誤: {error_msg}")
        
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
        print(f"\n--- API 請求失敗 (HTTP Error {e.response.status_code}) ---")
        print(f"**幣安錯誤信息:** {e.response.text.strip()}")
        print("請檢查 API Key 權限（尤其是 Enable Sub Account）。")
    except Exception as e:
        print(f"發生未知錯誤: {e}")

if __name__ == "__main__":
    main()
