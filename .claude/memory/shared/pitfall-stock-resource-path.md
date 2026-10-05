# pitfall-stock-resource-path

- Scope: shared
- Confidence: [觀]
- Trigger: STOCK_RESOURCE_PATH, 預設路徑, 資料根目錄, hardcode
- Tags: pitfall

## 知識

- **症狀**：`STOCK_RESOURCE_PATH` 環境變數未設時，舊管線與新管線讀寫的資料根目錄**不同**——資料寫在一邊、查詢去另一邊，查詢靜默回空（不報錯）
- **根因**：兩套預設值不同源
  - 舊管線：`define.py:4` 預設 `<PROJECT_ROOT>/StockResource`（即 `CrawlerTool/StockResource`；Windows 為 `E:\StockResource`），`define.py:7` 吃 env fallback
  - 新管線：各 script 自帶硬編碼 `DEFAULT_ROOT = "/Users/wellstseng/project/StockResource"`（`scripts/query_stock_data.py:16`、`build_parquet_dataset.py:17`、`backfill_aux.py:19`、`audit_local_data.py:12`、`download_data.py:12`、`update_stock_duckdb.py:11` 等 7+ 處），argparse `--root` 才吃 env fallback
- **解法**：一律顯式設 `STOCK_RESOURCE_PATH`（新舊管線都認這個 env），或新管線 script 明帶 `--root`；不要依賴預設值
- **適用條件**：同機混跑新舊管線、換機部署、公司端 Windows（新管線的 macOS 絕對路徑預設在 Windows 直接無效）
- **來源**：Phase C Q4 抽問發現（2026-07-02）；Phase E 實讀複核 file:line；併自 ext_20260702-1846 萃取 stub

## 行動

- 觸發同技術關鍵詞時主動提示此坑
- 不昇 global：專案特定佈局問題，非跨專案技術坑（Wells 2026-07-02 裁決）
