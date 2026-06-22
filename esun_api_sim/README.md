# 玉山證券 交易 API — 模擬（驗證）環境

參考官方前置文件：
<https://www.esunsec.com.tw/trading-platforms/api-trading/docs/prerequisites/#run_simulation>

## 資料夾結構（目標）

```
esun_api_sim/
├── config.simulation.ini.example   # 範本（進版控）
├── config.simulation.ini           # 真實金鑰（.gitignore，不進版控）
├── ID_DATE.p12                     # 你的憑證（.gitignore，不進版控）
├── index.py                        # 連線測試腳本
├── install.sh                      # venv + wheel 安裝
├── sdk/                            # 放 esun_trade-*.whl（手動下載）
└── .gitignore
```

## Checklist

### Part 1 — 申請服務（手動，審核 1–3 工作天）
- [ ] 登入交易 API 金鑰網站（證券帳號）
- [ ] 申請憑證 → 簽署同意書 → 送出
- [ ] 收到「申請完成通知」信

### Part 2 — 建模擬環境（審核通過後）
- [ ] 登入金鑰網站，匯出憑證 `ID_DATE.p12`（需憑證密碼），放進本資料夾
- [ ] 下載官方 `config.simulation.ini.example`（內含你的 Key/Secret）
- [ ] **加 IP 白名單**：把執行機器的 IP 加進「模擬 IP 白名單」
      （非固定 IP 可暫設 `0.0.0.0/0`，僅供開發測試）
- [ ] 把官方 config 改名 `config.simulation.ini`，`[Cert] Path` 填憑證路徑（例 `./ID_DATE.p12`）
- [ ] 從「SDK 下載」頁取得對應 Python 版本/平台的 `esun_trade-*.whl`，放進 `sdk/`
- [ ] `bash install.sh` 建環境裝套件
- [ ] `source .venv/bin/activate && python index.py` 連線測試
      （會提示輸入玉山登入密碼 + 憑證密碼）

成功後會收到「正式金鑰申請通知」信 → 代表模擬驗證完成，可申請正式環境。

## 注意
- 模擬環境**接單後不會撮合成交**，帳務/商品資訊也不保證與正式環境相同。
- 密碼輸錯：在腳本內呼叫 `sdk.reset_password()` 重設後再 `login()`。
- 行情 API（`esun_marketdata`）不分正式/模擬，要串即時行情另裝。
- 本機目前 Python 3.9.6，在 SDK 支援範圍（3.7–3.13）內。
