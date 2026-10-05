# CrawlerTool repo-patrol 巡檢規則與籌碼分析指令

- Scope: shared
- Author: catclaw-ext-merge
- Confidence: [臨]
- Trigger: repo-patrol, patrol-state.md, silent-no-change, 巡檢 cron 18:40, S0-S3 報告, chip_analysis.py --date
- Created-at: 2026-06-07
- Related: patrol-state

## 知識

- 巡檢 cron 於平日 18:40 自動執行；無變更時靜默只回一行，有變更時產生 S0-S3 報告。
- repo-patrol 沒偵測到變更時，仍要把 patrol-state.md 的 last-patrol 與 last-report 欄位更新為當天日期與 'silent-no-change' 狀態。
- 法人籌碼資料的每日處理指令是 `scripts/chip_analysis.py --date YYYY-MM-DD`。

## 行動

- 巡檢無變更時也要更新 patrol-state.md 的 last-patrol 與 last-report
