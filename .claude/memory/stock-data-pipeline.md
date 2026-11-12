# stock-data-pipeline

- Confidence: [固]
- Last-updated: 2026-06-10
- Scope: CrawlerTool / StockResource
- Source: unknown 2026-06-10（原對話已逾保留期）

## 知識

- [固] StockResource 資料根目錄是 `/Users/wellstseng/project/StockResource`。
- [固] Agent 查詢優先用 `scripts/query_stock_data.py` 或直接掛 Parquet 的 in-memory DuckDB；`stock.duckdb` 是給 DBeaver 使用的 view file。
- [固] `legal_person` 已正式納入每日 dataset：`download_data.py`、`build_parquet_dataset.py`、`query_stock_data.py`、`update_stock_duckdb.py`、`chip_analysis.py` 都已支援。
- [固] TWSE 三大法人 URL 必須用新版 `https://www.twse.com.tw/rwd/zh/fund/T86?date=YYYYMMDD&selectType=ALL&response=csv`；舊 `/fund/T86` 對部分歷史日期會回空白。
- [固] 截至 2026-06-10，`legal_person` Parquet/DuckDB 範圍為 2024-01-02 至 2026-06-10，row count 1,109,800。
- [固] 2024-01-01 至 2026-06-10 的 price 交易日對照 legal_person raw CSV，TWSE/TPEX 缺口皆為 0。
- [固] CrawlerTool 每日更新已由 CatClaw wrapper `/Users/wellstseng/.catclaw/workspace/agents/wendy/skills/crawler-market-data/scripts/run_daily_market_data.py` 整合，並掛 CatClaw 平日 21:10 排程；目前不在 CrawlerTool 內另建 `scripts/daily_update.py`。
- [固] CatClaw 21:10 市場資料排程 action 必須保留 `timeoutSec=1800`；exec 預設 120 秒會導致資料更新成功但排程狀態誤標 timeout。
- [固] 每日自動化不能只下載當日：wrapper 會用 recent window 補最近缺口，並用 `backfill_aux.py --start 20240101 --limit 20` 往前補融資融券 / 當沖 / 三大法人缺資料，再 build Parquet、刷新 DuckDB views、audit freshness、產出 chip_analysis。
- [固] 本機 Dashboard 入口是 `scripts/market_dashboard.py`，目前可由 tmux session `crawler_dashboard` 提供 `http://127.0.0.1:8765/`。
- [固] Dashboard 使用台股慣例：正數 / 上漲 / 買超顯示紅色，負數 / 下跌 / 賣超顯示綠色。

## 注意

- [觀] TWSE 有 `2025-04-03` legal_person raw/parquet，但本機 price 沒有該日；保留法人原始資料，不影響以 price 為主的 join。
- [觀] 2026-06-10 Wells 補充：有缺的資料就要往前補，不能只下載當日；已反映到 CatClaw wrapper 與 21:10 排程。
- [觀] 2026-06-10 實測 21:10 排程成功產出 `overall_status=ok`，price / margin / day_trading / legal_person 最新皆為 20260610 且 stale=False；同日已把 CatClaw cron timeout 從預設 120 秒補為 1800 秒。
