# CrawlerTool — AI 分析文件索引

> 本資料夾包含由 AI 輔助產出的專案分析文件。
> 最近更新：2026-06-07

---

## 文件清單

| # | 文件名稱 | 說明 |
|---|---------|------|
| 1 | Project_File_Tree.md | 專案資料夾結構、入口點、技術棧與風險摘要 |
| 2 | Stock_Data_Querying.md | StockResource 下載、Parquet 轉檔、DuckDB/DBeaver 與 Agent CLI 查詢流程 |

---

## 架構一句話摘要

CrawlerTool 是舊版 Python 股票資料爬蟲，負責抓取 TWSE/TPEX 股票清單與每日行情 CSV，整理後寫入 MongoDB，另有股票清單同步 MSSQL 的輔助腳本。

## 快速追蹤

| 主題 | 入口/檔案 |
|------|-----------|
| 每日股價下載與入庫 | `DailyTrade/daily_price2.py` |
| 股票清單下載與 CSV 輸出 | `StockList/loader.py` |
| 股票清單同步 MSSQL | `StockList/mssql.py` |
| MongoDB wrapper | `mongo.py` |
| URL、路徑、DB key 常數 | `define.py` |
| 檔案日期與路徑工具 | `global_func.py` |
| Raw CSV 轉 Parquet | `scripts/build_parquet_dataset.py` |
| Agent 股票資料查詢 | `scripts/query_stock_data.py` |
| DuckDB view 更新 | `scripts/update_stock_duckdb.py` |
| Agent 技術分析 | `scripts/technical_analysis.py` |
| Agent 籌碼分析 | `scripts/chip_analysis.py` |

## 重要注意

- 專案目前規模小：掃描到 16 個非排除檔案，其中 Python 原始碼 8 個。
- `Requirements.txt` 是 UTF-16 little-endian + CRLF，不是一般 UTF-8 requirements 格式。
- 多處硬編碼 Windows 路徑、內網 DB 位址與認證資訊；文件不重複列出密碼，改碼前需直接檢查原始碼。
- 外部資料源已於 2026-06-05 實測更新為 HTTPS；每日行情 parser 已改用欄位名稱正規化，不再依賴舊行長度判斷。
- TPEX 每日行情需使用 `https://www.tpex.org.tw/www/zh-tw/afterTrading/dailyQuotes?date=YYYY/MM/DD&id=&response=csv`；舊 `stk_quote_result.php` 目前會忽略日期並回最新資料，不可用於歷史補檔。
- 已驗證 2026-06-04 TWSE/TPEX 每日行情下載與正規化；股票清單 ISIN 市場 2/4 live parser 可解析。
