"""
玉山證券 交易 API — 模擬環境連線測試
參考：https://www.esunsec.com.tw/trading-platforms/api-trading/docs/prerequisites/#run_simulation

執行前置：
  - 已安裝 esun_trade（見 install.sh）
  - 同資料夾內有 config.simulation.ini 與憑證檔（.p12）
執行：
  python index.py
  → 會提示輸入「玉山證券登入密碼」與「憑證密碼」

說明：
  下面用「跌停價買 1 張」作連線測試委託 —— 模擬環境不會成交，且跌停買單也不會撮合，
  純粹驗證登入 + 下單通道是否打通。成功會印出 order 結果。
"""
from configparser import ConfigParser

from esun_trade.sdk import SDK
from esun_trade.order import OrderObject
from esun_trade.constant import APCode, Trade, PriceFlag, BSFlag, Action

CONFIG_PATH = "./config.simulation.ini"


def main():
    config = ConfigParser()
    if not config.read(CONFIG_PATH):
        raise SystemExit(f"找不到設定檔：{CONFIG_PATH}（請先由 config.simulation.ini.example 建立）")

    sdk = SDK(config)
    sdk.login()  # 互動式輸入登入密碼與憑證密碼

    order = OrderObject(
        buy_sell=Action.Buy,
        price_flag=PriceFlag.LimitDown,  # 跌停價，測試用不會成交
        price=None,
        stock_no="2884",                   # 玉山金（自家股，純測試）
        quantity=1,
    )
    result = sdk.place_order(order)
    print("下單通道測試完成，回應：")
    print(result)


if __name__ == "__main__":
    main()
