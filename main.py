import requests
import os

# 幣安 U 本位合約 API 基礎 URL
BASE_FUTURES_URL = 'https://fapi.binance.com'

def test_railway_connection():
    """ 測試 Railway 預設 IP 是否能連接到幣安的公開端點。 """
    
    endpoint = '/fapi/v1/exchangeInfo' # 完全公開的交易規則查詢
    url = BASE_FUTURES_URL + endpoint

    print("--- 正在測試 Railway 預設 IP 連線 ---")
    
    try:
        # 直接發送請求，不帶任何 API Key, Secret 或簽名
        response = requests.get(url, timeout=15)
        
        # 檢查 HTTP 狀態碼
        response.raise_for_status() 
        
        if response.status_code == 200:
            print("\n** 測試結果：連線成功 (200 OK) **")
            print("Railway 的預設 IP 範圍是**可以**連接幣安的！")
            print("您現在可以將程式碼換回原本的版本，失敗的原因很可能在於 API 權限或簽名。")
            # 為了驗證，打印響應長度 (ExchangeInfo 通常很大)
            print(f"成功接收數據長度: {len(response.text)} bytes")

    except requests.exceptions.HTTPError as e:
        print(f"\n** 測試結果：連線失敗 (錯誤碼 {e.response.status_code}) **")
        print(f"響應內容: {e.response.text.strip()}")
        if e.response.status_code == 403:
            print("結論：Railway 的預設 IP 範圍**也被幣安的 CloudFront 封鎖**。")
            print("您必須啟用靜態 IP 地址才能繼續。")
        else:
            print("發生其他 HTTP 錯誤，請檢查 URL。")
            
    except requests.exceptions.RequestException as e:
        print(f"\n** 網路或連線錯誤: {e} **")
        print("可能是 DNS 或連線超時，請重試。")


if __name__ == "__main__":
    test_railway_connection()
