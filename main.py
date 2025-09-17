import os
import requests
from binance.client import Client
from binance.exceptions import BinanceAPIException
import logging

# 配置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- 【環境變數設定】---
# 請在 Railway 變數中填入子帳號的 Key/Secret
API_KEY = os.environ.get('SUB_ACCOUNT_API_KEY') # 使用子帳號的 Key
API_SECRET = os.environ.get('SUB_ACCOUNT_SECRET') # 使用子帳號的 Secret
SYMBOL = os.environ.get('SYMBOL', 'DOGEUSDC') 
TARGET_LEVERAGE = int(os.environ.get('TARGET_LEVERAGE', 20)) # 設定你想要的槓桿倍數

# 創建通用的 Client 客戶端
# 由於 Client 內部邏輯是針對單一帳戶，所以直接使用子帳號的 Key 即可操作該子帳號
client = Client(API_KEY, API_SECRET) 

def set_target_leverage(symbol: str, leverage: int):
    """
    使用子帳號自己的 API Key 設定槓桿。
    """
    logging.info(f"-> 正在嘗試設定 {symbol} 的槓桿為 {leverage} 倍...")
    
    try:
        # **關鍵：直接使用 futures_change_leverage**
        result = client.futures_change_leverage(symbol=symbol, leverage=leverage)
        
        logging.info("   ✅ 槓桿設定成功！")
        logging.info(f"   設定結果: {result}")
        return True
    
    except BinanceAPIException as e:
        error_msg = str(e)
        logging.error(f"   ❌ 設定失敗：幣安 API 錯誤: {error_msg}")
        return False
    except Exception as e:
        logging.error(f"   ❌ 設定失敗，發生非 API 錯誤: {str(e)}")
        return False


def main():
    if not all([API_KEY, API_SECRET]):
        logging.error("錯誤：請檢查 Railway 環境變數是否設定完整 (子帳號 Key/Secret)。")
        return

    logging.info("--- 正在執行子帳號合約槓桿設置 ---")

    # 執行槓桿設定
    set_target_leverage(SYMBOL, TARGET_LEVERAGE)
        

if __name__ == "__main__":
    main()
