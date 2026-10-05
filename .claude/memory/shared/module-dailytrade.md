# module-dailytrade

- Scope: shared
- Confidence: [臨]
- Trigger: DailyTrade, daily_price2, 每日行情, 行情下載, MongoDB, mongo, 入庫, upsert
- Tags: L1

## 知識

- **職責**：舊主流程——下載 TWSE/TPEX 每日行情 CSV → 欄名正規化 → pandas 讀取 → 逐股 upsert 進 MongoDB `stock.Stock_<id>`
- **關鍵檔**：
  - `DailyTrade/daily_price2.py` — 全流程單檔：`get_mongo_mgr`:22（`STOCK_MONGO_URL` 可覆寫，預設 hardcode 192.168.1.14）、`normalize_file`:72（欄位名對映）、`parse_file_to_db`:115（巢狀 `items.<YYYYMMDD>.<key>`，upsert:154）、`load_range`:182（主迴圈，encoding ms950:208）、`__main__`:233
  - `DailyTrade/test.py` — 讀上市/上櫃 id 的小測試
- **依賴**：`StockList/loader.py`（read_stock_ids 過濾入庫清單）、`global_func.py`（daterange / get_latest_file_date）、`define.py`、`mongo.py`
- **坑**：`global_func.py` 的 `daterange`:6 是**倒序遞減** yield，呼叫端要注意方向；停牌判斷用字串 `"--"`（:132）；`check_update_latest_day`:167 hardcode ObjectId

## 行動

- 回答此模組問題前，回讀上列關鍵檔取證
