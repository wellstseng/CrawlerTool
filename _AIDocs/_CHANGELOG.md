# CrawlerTool — AI 分析文件變更記錄

| 日期 | 變更 |
|------|------|
| 2026-06-07 | 新增 `scripts/query_stock_data.py` 與 `Stock_Data_Querying.md`：提供 Agent 以 JSON/CSV/table 查詢 price/margin/day_trading/stock_list，並記錄 DBeaver/DuckDB/Parquet 查詢方式。 |
| 2026-06-07 | 新增 `scripts/build_parquet_dataset.py`：將 `StockResource` raw CSV 正規化為 Parquet，支援 price/margin/day_trading/stock_list、日期區間、壞檔 manifest 與可選 DuckDB 驗證。 |
| 2026-06-05 | 補齊外部歷史股價 CSV：以 `/Users/wellstseng/project/StockResource` 為資料根目錄，補到 2026-06-04；確認 TPEX 舊 `stk_quote_result.php` 會忽略日期，改用新版 `www/zh-tw/afterTrading/dailyQuotes` 並加資料日期檢查。 |
| 2026-06-05 | 修復股票爬蟲 URL 與新版 CSV 解析：TWSE/TPEX/ISIN 改用 HTTPS，TPEX 19 欄與 TWSE 新版每日行情可正規化為入庫欄位；Mongo wrapper 改用新版 PyMongo API。 |
| 2026-06-05 | 知識庫建立：新增 `_AIDocs` 索引、專案結構摘要與專案記憶工作流骨架。 |
