# module-stocklist

- Scope: shared
- Confidence: [臨]
- Trigger: StockList, 股票清單, stock list, ISIN, loader, MSSQL, 上市, 上櫃
- Tags: L1

## 知識

- **職責**：從 TWSE ISIN 頁抓上市(2)/上櫃(4)股票清單，輸出 CSV；另可寫入 MSSQL
- **關鍵檔**：
  - `StockList/loader.py` — 抓 `isin.twse.com.tw/isin/C_public.jsp?strMode={2|4}`，BeautifulSoup 解析（:79-97）；雙輸出 `list_{2|4}.csv` + 正規化版 `StockResource/data/list*.csv`；`read_stock_ids`:106 供 daily_price2 用；`__main__`:115
  - `StockList/mssql.py` — 清單 CSV → `dbo.StockInfo` insert-if-not-exists（:17-45）
- **依賴**：define（URL）、requests/bs4；mssql.py 依 pymssql
- **坑**：`mssql.py`:20-24 hardcode 內網 MSSQL 位址與明文帳密（極高風險，勿外流）；`loader.py`:71 用 str.replace 湊 JSON，特殊字元脆弱

## 行動

- 回答此模組問題前，回讀上列關鍵檔取證
