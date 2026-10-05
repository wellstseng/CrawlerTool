# project-overview

- Scope: shared
- Confidence: [觀]
- Trigger: CrawlerTool, 專案總覽, 架構, architecture, 技術棧, tech stack, 股票爬蟲
- Tags: L0

## 知識

- **是什麼**：台股資料爬蟲 + 分析工具——抓 TWSE/TPEX 行情與籌碼，落 raw CSV，供 MongoDB（舊）與 Parquet/DuckDB（新）兩條管線使用
- **技術棧**：Python；requests / beautifulsoup4 / pymongo / pandas / twstock（`Requirements.txt`，UTF-16 LE 編碼）；新管線另用 duckdb / pyarrow（未列入 Requirements，已脫節）
- **模組地圖**：
  - `define.py` — 常數中心：路徑格式、來源 URL、headers、MarketType/DataType/DB_KEY
  - `global_func.py` — 日期與路徑工具
  - `mongo.py` — MongoManager PyMongo wrapper
  - `DailyTrade/` — 舊主流程：下載每日行情 CSV → 正規化 → 寫 MongoDB
  - `StockList/` — 股票清單抓取（ISIN 頁）與 MSSQL 寫入
  - `scripts/` — 新 DuckDB/Parquet 管線：下載/轉檔/查詢/技術分析/籌碼/Dashboard
  - `_AIDocs/` — AI 專案文件（_INDEX / Stock_Data_Querying / Project_File_Tree / _CHANGELOG）
- **入口點**：無統一 entrypoint，各流程走各自 `__main__`；舊主流程 `DailyTrade/daily_price2.py:233`；新下載 CLI `scripts/download_data.py:154`；查詢 CLI `scripts/query_stock_data.py:267`。每日排程在 repo 外由 CatClaw wrapper 串接
- **建置/執行**：見 `_AIDocs/Stock_Data_Querying.md`（下載→build parquet→view→查詢）；資料根目錄以環境變數 `STOCK_RESOURCE_PATH` 覆寫（`define.py:7`），實際資料在 repo 外 `/Users/wellstseng/project/StockResource`
- **VCS**：git，主幹 main（local）

## 行動

- 細節問題 → 依模組地圖找對應 L1 atom → 回讀原檔
