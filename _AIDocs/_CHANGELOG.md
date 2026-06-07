# CrawlerTool — AI 分析文件變更記錄

| 日期 | 變更 |
|------|------|
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
