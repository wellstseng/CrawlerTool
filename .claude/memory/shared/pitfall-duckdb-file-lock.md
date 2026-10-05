# pitfall-duckdb-file-lock

- Scope: shared
- Confidence: [觀]
- Trigger: duckdb, 鎖檔, file lock, DBeaver, database is locked
- Tags: pitfall

## 知識

- **症狀**：程式查詢 .duckdb 檔失敗 / 卡住，或 GUI 打不開
- **根因**：DuckDB 檔案是單一寫入者；DBeaver 等 GUI 開著連線就持鎖，CLI/程式再連同一檔會衝突
- **解法**：程式查詢改用 in-memory DuckDB 直接掛 Parquet（`read_parquet` view），實體 .duckdb 只放 view 給 GUI 用
- **適用條件**：任何「GUI + 程式」同時要讀 DuckDB 檔的場景
- **來源**：CrawlerTool / 2026-07-02 / `scripts/query_stock_data.py`:60-66 + `_AIDocs/Stock_Data_Querying.md`:16

## 行動

- 觸發同技術關鍵詞時主動提示此坑
- 跨專案共享候選：建議昇 global（待 Wells 點頭）
