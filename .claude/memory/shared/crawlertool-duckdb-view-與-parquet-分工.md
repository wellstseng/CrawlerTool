# CrawlerTool DuckDB view 與 Parquet 分工

- Scope: shared
- Author: catclaw-ext-merge
- Confidence: [臨]
- Trigger: DuckDB view, stock.duckdb, Parquet 實體儲存
- Created-at: 2026-07-02

## 知識

- CrawlerTool 的 DuckDB 採 view 設計：資料實體存在 Parquet 檔，`stock.duckdb` 只存 view 定義，避免每次更新都要重新 load 整個資料集（2026-07-02）。

## 行動

- （依知識內容判斷）
