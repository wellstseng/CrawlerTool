# decision-storage-design

- Scope: shared
- Confidence: [臨]
- Trigger: 儲存設計, storage, 為什麼 parquet, 為什麼 duckdb, why mongo, 選型, 資料佈局
- Tags: decision

## 知識

- **決策**：raw CSV 為來源真相（不修改）→ Parquet 為分析主資料 → `stock.duckdb` 只放 view（給 DBeaver）→ Agent 查詢用 in-memory DuckDB 掛 Parquet；舊 MongoDB 管線並存未棄用
- **理由**（文件記載）：raw CSV 保留追溯；Agent 查詢不依賴 stock.duckdb 是為了避開 DBeaver 鎖檔（in-memory 不受鎖影響）
- **出處**：`_AIDocs/Stock_Data_Querying.md`:16, :31-36, :537
- **未記載**：「當初為何選 MongoDB」與「為何從 Mongo 遷往 Parquet/DuckDB」的 rationale 文件與註解皆無；_CHANGELOG 只記「新增」Parquet 工具（:16,17），未記棄用 Mongo 的決定——現況是兩套並存的遷移現象
- **影響範圍**：scripts/ 全部查詢分析工具走 Parquet；DailyTrade 入庫仍寫 Mongo

## 行動

- 被問儲存選型時，明確區分「文件有記載的理由」與「未記載只能觀察現況」
