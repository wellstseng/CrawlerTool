# CrawlerTool — 專案結構摘要

> 掃描日期：2026-06-05

## 專案概況

- 類型：Python 股票資料爬蟲 / 資料匯入腳本。
- 規模：16 個非排除檔案，8 個 Python 原始碼檔。
- 主要資料源：TWSE、TPEX 的股票清單、每日收盤行情 CSV/HTML。
- 主要儲存：MongoDB；另有 MSSQL 同步輔助腳本。
- 執行模式：沒有統一 app entrypoint，各資料流程由個別 script 的 `__main__` 啟動。

## 目錄結構

```text
CrawlerTool/
├── DailyTrade/
│   ├── daily_price2.py      # 每日行情下載、CSV 正規化、MongoDB upsert
│   └── test.py              # 讀取上市/上櫃股票清單的簡易測試腳本
├── StockList/
│   ├── loader.py            # 從 TWSE ISIN 頁面抓股票清單並輸出 list_*.csv
│   ├── mssql.py             # 將股票清單 CSV 寫入 MSSQL
│   ├── list_2.csv           # 上市清單資料
│   ├── list_4.csv           # 上櫃清單資料
│   └── test.txt             # loader 測試資料
├── define.py                # 路徑、URL、request headers、MarketType、DB key 常數
├── global_func.py           # 日期 range、最新 CSV 日期、路徑工具
├── mongo.py                 # MongoManager wrapper
├── temp.py                  # Mongo collection 檢查/清理輔助腳本
└── Requirements.txt         # UTF-16 LE 套件版本清單
```

## 入口點

| 檔案 | 用途 |
|------|------|
| `DailyTrade/daily_price2.py` | 預設下載 TWSE/TPEX 每日行情並寫入 MongoDB。 |
| `StockList/loader.py` | 依命令列參數抓取指定市場股票清單。 |
| `StockList/mssql.py` | 依命令列參數讀取 `list_*.csv` 並同步到 MSSQL。 |
| `temp.py` | 列出 MongoDB 中名稱包含 `DailyInfo_` 的 collection，drop 行為目前註解。 |

## 技術棧

| 類別 | 掃描結果 |
|------|----------|
| 語言 | Python |
| HTTP | `requests` |
| HTML parsing | `beautifulsoup4` |
| CSV/DataFrame | `csv`, `pandas` |
| MongoDB | `pymongo`, `MongoManager` |
| MSSQL | `pymssql` |
| 股票代碼判斷 | `twstock` |

`Requirements.txt` 內含 Django、Flask、Celery 等套件 pins，但目前掃描到的原始碼沒有 web app 或 worker entrypoint；可能是舊環境整包 freeze。

## 資料流程

```text
StockList/loader.py
  -> TWSE ISIN HTML
  -> parse 股票/ETF rows
  -> StockList/list_2.csv, StockList/list_4.csv

DailyTrade/daily_price2.py
  -> 依 define.py URL 抓 TWSE/TPEX 每日行情
  -> 寫入 Define.FILE_PATH 底下的 CSV
  -> normalize_file()
  -> pandas read_csv()
  -> MongoDB stock.Stock_<stock_id> upsert
  -> stock.Outline 更新最新日期

StockList/mssql.py
  -> 讀 StockList/list_*.csv
  -> 補 IndustryType
  -> dbo.StockInfo insert-if-not-exists
```

## 風險與約束

- `define.py` 使用 Windows 絕對路徑 `E:\StockResource`，macOS 本機直接跑會找不到資料根目錄。
- DB 連線資訊與認證硬編碼在原始碼內；任何測試都可能打到真實內網資料庫。
- CSV parser 依賴 TWSE/TPEX 舊欄位順序、中文欄名與行長度判斷，外部網站格式改版會直接影響流程。
- `mongo.py` 使用較舊的 PyMongo API，例如 `collection.update()`、`collection_names()`。
- `Requirements.txt` 是 UTF-16 LE；安裝前需先確認 pip 是否能接受，必要時再轉成 UTF-8。

## 後續建議分析

1. 先盤點哪些 script 仍在使用，避免維護已廢棄流程。
2. 把 DB 連線、資料根目錄、外部 URL 從原始碼抽成設定，但不要在未確認部署環境前大改。
3. 建立最小 smoke test：以本地 fixture 驗證 `loader.py` 與 `daily_price2.py` parser。
