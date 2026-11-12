# CrawlerTool — AI 分析文件變更記錄

| 日期 | 變更 |
|------|------|
| 2026-06-10 | 驗證 CatClaw 21:10 市場資料排程已成功更新 2026-06-10 資料；price / margin / day_trading / legal_person freshness 均對齊當日，並將 cron exec `timeoutSec` 補為 1800 秒避免成功更新被誤標 timeout。 |
| 2026-06-10 | 調整 `scripts/market_dashboard.py` 漲跌色彩為台股慣例：正數/上漲/買超用紅色，負數/下跌/賣超用綠色；同步更新專案記憶。 |
| 2026-06-10 | CatClaw `crawler-market-data` wrapper 已整合每日自動化並掛平日 21:10 排程：最近視窗下載、`backfill_aux.py` 往前補缺、Parquet build、DuckDB views、audit 與 chip_analysis；每日自動化不只下載當日。 |
| 2026-06-10 | 更新專案記憶與 `Stock_Data_Querying.md`：記錄目前尚無 `scripts/daily_update.py`，也沒有 CrawlerTool cron/launchd 排程；每日更新仍需手動串接下載、轉檔、DuckDB view、freshness audit 與籌碼 JSON。 |
| 2026-06-10 | 將 TWSE 三大法人 URL 改為新版 `rwd/zh/fund/T86`，補齊 `legal_person` raw/Parquet 自 2024-01-01 至 2026-06-09；`legal_person` DuckDB row count 增至 1,107,782，freshness 與 price 對齊至 2026-06-09。 |
| 2026-06-09 | 新增 `scripts/market_dashboard.py` 本機單頁 Dashboard，提供市場總覽、技術條件掃描、三大法人/產業資金流、融資/當沖排行、背離訊號與單股技術圖表；讀 Parquet/DuckDB view 與既有籌碼 JSON，不修改資料。 |
| 2026-06-07 | 新增 `scripts/chip_analysis.py`：產出 `StockResource/analysis/YYYY-MM-DD_chip_analysis.json`，包含三大法人總買賣超、法人排行、產業資金流、融資增減、當沖熱度與價量/法人/融資背離訊號；`audit_local_data.py` 新增 `--freshness` 檢查 legal_person 等 dataset 最新日期。 |
| 2026-06-07 | 擴充 `scripts/technical_analysis.py`：新增 `screen` 全市場技術條件掃描與 `market-summary` 市場結構摘要，支援突破/跌破、均線排列、爆量、RSI、MACD、52 週高低等 preset。 |
| 2026-06-07 | 新增 `legal_person` 三大法人資料管線：下載 raw CSV、轉 Parquet、Agent CLI 查詢、joined 分析欄位與 `update_stock_duckdb.py` view 更新工具；已驗證 2026-06-05 TWSE/TPEX 單日資料。 |
| 2026-06-07 | 新增 `scripts/technical_analysis.py`：提供 Agent 單股技術分析 CLI，支援 SMA/EMA/RSI/MACD/KD/Bollinger/ATR/量均線/關鍵價位/訊號與 warnings，並預設排除疑似單日異常價。 |
| 2026-06-07 | 更新股票主檔：`StockList/loader.py` 納入創新板與 TDR，並同步輸出到 `StockResource/data/list*.csv`；重建 `stock_list` Parquet 至 2,322 筆，最新 4 碼可交易標的覆蓋率為 100%。 |
| 2026-06-07 | 新增 `scripts/query_stock_data.py` 與 `Stock_Data_Querying.md`：提供 Agent 以 JSON/CSV/table 查詢 price/margin/day_trading/stock_list，並記錄 DBeaver/DuckDB/Parquet 查詢方式。 |
| 2026-06-07 | 新增 `scripts/build_parquet_dataset.py`：將 `StockResource` raw CSV 正規化為 Parquet，支援 price/margin/day_trading/stock_list、日期區間、壞檔 manifest 與可選 DuckDB 驗證。 |
| 2026-06-05 | 補齊外部歷史股價 CSV：以 `/Users/wellstseng/project/StockResource` 為資料根目錄，補到 2026-06-04；確認 TPEX 舊 `stk_quote_result.php` 會忽略日期，改用新版 `www/zh-tw/afterTrading/dailyQuotes` 並加資料日期檢查。 |
| 2026-06-05 | 修復股票爬蟲 URL 與新版 CSV 解析：TWSE/TPEX/ISIN 改用 HTTPS，TPEX 19 欄與 TWSE 新版每日行情可正規化為入庫欄位；Mongo wrapper 改用新版 PyMongo API。 |
| 2026-06-05 | 知識庫建立：新增 `_AIDocs` 索引、專案結構摘要與專案記憶工作流骨架。 |
