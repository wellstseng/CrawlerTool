# StockResource Parquet 結構與法人籌碼資料鏈

- Scope: shared
- Author: catclaw-ext-merge
- Confidence: [臨]
- Trigger: build_parquet_dataset.py, StockResource/parquet, stock.duckdb view, legal_person view, chip_analysis.json, download_data.py, 三大法人 盤後分析, Parquet schema
- Created-at: 2026-06-07
- Related: module-scripts-pipeline, pitfall-stock-resource-path

## 知識

- /Users/wellstseng/project/CrawlerTool/scripts/build_parquet_dataset.py 第 18 行起定義市場資料 Parquet schema 的標準欄位。
- /Users/wellstseng/project/StockResource/parquet 存放 price、day_trading、legal_person、stock_list 的 Parquet 檔，依市場（TWSE/TPEX）與日期（year-YYYY/YYYYMMDD.parquet）分層。
- crawler-market-data skill 用 CrawlerTool 的 download_data.py 從 TWSE 與 TPEX 抓盤後資料，含量價、融資融券、法人買賣。
- 2026-06-07 時 stock.duckdb 只有 price、margin、day_trading、stock_list 四個 view，沒有 legal_person；每日盤後市場分析摘要也尚未納入三大法人，雖然資料已在 legal_person 表與 market_data_adapter.py 可取得。
- 2026-06-07 的補強計畫：加 legal_person dataset 的 freshness 檢查、refresh stock.duckdb 加入 legal_person view、盤後分析報告加入法人摘要與排行。
- chip_analysis.json 的籌碼分析層包含：法人買賣量、類股資金流向、融資變化、當沖熱度、背離訊號。
- investment-daily-advisor 讀取的籌碼分析檔是 ~/project/StockResource/analysis/YYYY-MM-DD_chip_analysis.json。
- 查詢時用分開的表（price、技術分析、margin）而非 join 過的表，避免 inner join 因某表欄位過期而截斷資料。

## 行動

- （依知識內容判斷）
