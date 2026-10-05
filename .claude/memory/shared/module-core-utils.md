# module-core-utils

- Scope: shared
- Confidence: [觀]
- Trigger: define, 常數, constants, global_func, mongo.py, 路徑, URL, headers, DB_KEY
- Tags: L1

## 知識

- **職責**：三個共用基座——常數中心 / 日期路徑工具 / Mongo wrapper
- **關鍵檔**：
  - `define.py` — `FILE_PATH`:7（`STOCK_RESOURCE_PATH` 覆寫）、路徑格式:13-18、TWSE/TPEX/T86 URL:67-93、`get_market_type`:112（twstock）、`MarketType`:126 / `DataType`:139 / `DB_KEY`:148
  - `global_func.py` — `daterange`:6（倒序）、`get_latest_file_date`:10（找不到回 "2000/1/1"）、`get_abs_path`:24
  - `mongo.py` — `MongoManager`:6，`upsert`:17 用 update_one+upsert 並保留舊回傳格式相容
- **依賴**：無（被其他模組依賴的底層）
- **坑**：`define.py` headers 內含過期 Cookie（:50,73）；`DB_KEY.DATE` 定義兩次（:150,182）

## 行動

- 回答此模組問題前，回讀上列關鍵檔取證
