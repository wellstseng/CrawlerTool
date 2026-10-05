# doc-index

- Scope: shared
- Confidence: [觀]
- Trigger: 檔案在哪, 哪個檔, where is, doc index, 文件索引
- Tags: L2

## 知識

| 路徑 | 一句話職責 |
|---|---|
| `define.py` | 常數中心（路徑格式/URL/headers/DB_KEY） |
| `global_func.py` | 日期與路徑工具 |
| `mongo.py` | MongoManager PyMongo wrapper |
| `temp.py` | 列 DailyInfo_ collections（drop 已註解） |
| `DailyTrade/daily_price2.py` | 舊主流程：行情下載→正規化→Mongo |
| `StockList/loader.py` | ISIN 股票清單抓取 |
| `StockList/mssql.py` | 清單寫 MSSQL（hardcode 帳密，勿外流） |
| `scripts/download_data.py` | 統一下載 CLI |
| `scripts/backfill_aux.py` | margin/day_trading/legal_person 抓取 |
| `scripts/build_parquet_dataset.py` | raw CSV → Parquet |
| `scripts/query_stock_data.py` | 查詢核心（in-memory DuckDB） |
| `scripts/update_stock_duckdb.py` | stock.duckdb view 更新（DBeaver 用） |
| `scripts/technical_analysis.py` | 技術分析 analyze/screen/market-summary |
| `scripts/chip_analysis.py` | 籌碼分析 JSON |
| `scripts/audit_local_data.py` | raw CSV 完整性稽核 |
| `scripts/market_dashboard.py` | 本機 Dashboard |
| `_AIDocs/_INDEX.md` | 文件索引 + 重要注意事項 |
| `_AIDocs/Stock_Data_Querying.md` | 資料管線全文件（下載→轉檔→查詢） |
| `_AIDocs/Project_File_Tree.md` | 目錄樹/入口點/技術棧/資料流圖 |
| `_AIDocs/_CHANGELOG.md` | 時間序變更記錄 |

## 行動

- 「XX 在哪個檔」類問題直接查表 → 回讀該檔確認後作答
