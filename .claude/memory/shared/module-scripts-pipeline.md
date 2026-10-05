# module-scripts-pipeline

- Scope: shared
- Confidence: [觀]
- Trigger: scripts, 查詢, query, parquet, duckdb, 技術分析, technical analysis, 籌碼, dashboard, 下載, download
- Tags: L1

## 知識

- **職責**：新分析管線——raw CSV 下載、Parquet 轉檔、DuckDB 查詢、技術/籌碼分析、本機 Dashboard
- **關鍵檔**：
  - `scripts/download_data.py` — 統一下載 CLI（price 委派 daily_price2、aux 走 backfill_aux，`main`:94）
  - `scripts/backfill_aux.py` — margin / day_trading / legal_person raw CSV 抓取
  - `scripts/build_parquet_dataset.py` — raw CSV → Parquet（pyarrow 固定 schema:24-70，支援 --verify）
  - `scripts/query_stock_data.py` — 查詢核心：in-memory DuckDB 掛 Parquet view（`connect`:60-66；`command_query`:152、`command_joined`:174）
  - `scripts/update_stock_duckdb.py` — 對實體 stock.duckdb 建 view（給 DBeaver，:35-41）
  - `scripts/technical_analysis.py` — analyze / screen / market-summary（main:646）
  - `scripts/chip_analysis.py` — 籌碼分析 JSON 產出
  - `scripts/audit_local_data.py` — raw CSV 完整性/新鮮度稽核
  - `scripts/market_dashboard.py` — http.server 單頁 Dashboard（唯讀，預設 127.0.0.1:8765）
- **依賴**：define（路徑/URL）、DailyTrade（price 下載）、外部資料根 `STOCK_RESOURCE_PATH`
- **坑**：technical_analysis 用未復權價，`--adjusted` 目前會失敗（`_AIDocs/Stock_Data_Querying.md`:283）；DBeaver 開著會鎖 stock.duckdb（同文件:414）

## 行動

- 回答此模組問題前，回讀上列關鍵檔取證
