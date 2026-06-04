# CrawlerTool — 專案導讀 (Claude Code)

> 舊版 Python 股票資料爬蟲，抓取 TWSE/TPEX 股票清單與每日行情，整理後寫入 MongoDB，另有 MSSQL 同步輔助腳本。

## 風險分級（專案特定）

> 通用分級框架見全域 `~/.claude/CLAUDE.md`。

| 風險等級 | 本專案操作類型 | 驗證要求 |
|---------|--------------|---------|
| **高** | 修改 TWSE/TPEX 解析、CSV 正規化、MongoDB upsert 結構、股票代碼篩選、Requirements 編碼/依賴 | 必須先讀 `_AIDocs/Project_File_Tree.md` 與相關原始碼，並用 fixture 或實際下載樣本驗證 |
| **極高** | 實際連線內網 MongoDB/MSSQL、drop collection、修改硬編碼認證、批次重跑入庫、改變資料目錄策略 | 必須向使用者確認後才執行 |

## 技術約束

- Python 舊專案，沒有統一 app entrypoint；各流程由 script 的 `__main__` 啟動。
- `define.py` 內含主要 URL、request headers、資料路徑與 DB key 常數。
- `Define.FILE_PATH` 目前指向 Windows 絕對路徑 `E:\StockResource`。
- DB 連線資訊硬編碼於原始碼；文件不重複列出密碼。
- `Requirements.txt` 是 UTF-16 little-endian + CRLF。
- 外部資料源格式不穩定，改 parser 時要以樣本驗證，不能只靠靜態推測。

## 開工規則

- 開工前先讀 `_AIDocs/_INDEX.md`，再依任務讀對應原始碼。
- 不主動重構全專案；優先做最小範圍修正。
- 未經確認不要執行會連線真實 DB 或大量下載/寫入資料的 script。
