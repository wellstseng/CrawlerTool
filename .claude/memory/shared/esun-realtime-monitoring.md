# esun-realtime-monitoring

- Scope: shared
- Author: wellstseng
- Confidence: [臨]
- Trigger: 玉山 API, esun, esun_stock_worker, 即時盤中, 盤中監控, 即時行情, 個股監控
- Created-at: 2026-07-02
- Related: bridge-vague-ping-response
- Source: unknown 2026-07-02（原對話已逾保留期）

## 知識

- [臨] Wells 已提需求：用玉山 API 取得指定個股即時盤中資料 + 監控等功能，2026-06-22 起了頭但中途按「暫停」，尚未給具體方向
- [臨] 玉山 API 模擬環境 esun_api_sim 已於 commit 77de6cd 搬出至獨立 repo /Users/wellstseng/project/esun_stock_worker（不在 CrawlerTool 內）
- [臨] CrawlerTool 現有能力是盤後批次爬蠻（TWSE/TPEX 每日行情→MongoDB）+ Parquet/DuckDB 查詢 + 技術/籌碼分析 CLI；即時盤中是全新領域，马接到獨立 repo

## 行動

- 接續玉山即時監控 → 先讀 /Users/wellstseng/project/esun_stock_worker 現狀，確認是哪個玉山 API（下單/行情）及認證方式後再規劃
- 架構級任務先用 Plan Mode（architecture 首次正確率低）
