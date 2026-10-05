# CrawlerTool 路徑常數與 chip_analysis 資料集

- Scope: shared
- Author: catclaw-ext-merge
- Confidence: [臨]
- Trigger: define.py, MARGIN_PATH_FMT, DAILY_PRICE_FMT, StockResource 路徑, chip_analysis.py, legal_person dataset, freshness audit, CrawlerTool 路徑
- Created-at: 2026-06-07

## 知識

- 專案目錄為 `/Users/wellstseng/project/CrawlerTool`，資料目錄為 `/Users/wellstseng/project/StockResource`。
- `/Users/wellstseng/project/CrawlerTool/define.py` 定義資料路徑與 URL 常數，例如 `MARGIN_PATH_FMT`、`DAYTRADING_PATH_FMT`、`DAILY_PRICE_FMT`。
- 踩坑（2026-07-02）：舊管線 `define.py` 用相對路徑 `CrawlerTool/StockResource`，新 CLI／build 用絕對路徑 `~/project/StockResource`，兩者不一致。
- StockResource 是純資料層，沒有 .py 檔；投資邏輯位於 skill scripts 與 CrawlerTool（2026-07-01）。
- `scripts/chip_analysis.py` 輸出結構化籌碼分析 JSON 到 `~/project/StockResource/analysis/YYYY-MM-DD_chip_analysis.json`。
- `legal_person` 已正式納入每日 dataset，並在 freshness audit 檢查其日期；2026-06-05 的資料已驗證可用，chip_analysis.py 能產出完整的籌碼分析 JSON。

## 行動

- （依知識內容判斷）
