# Stock Data Pipeline

> 更新：2026-06-07

## 結論

股票分析資料目前採用：

```text
raw CSV：/Users/wellstseng/project/StockResource/data/
Parquet：/Users/wellstseng/project/StockResource/parquet/
DuckDB view file：/Users/wellstseng/project/StockResource/stock.duckdb
Agent CLI：scripts/query_stock_data.py
```

Agent 優先使用 `scripts/query_stock_data.py`，不要直接連 DBeaver 開著的 `stock.duckdb`。原因是 DuckDB 檔案會被 GUI 鎖住；CLI 會用 in-memory DuckDB 直接掛 Parquet，不受鎖檔影響。

## Pipeline

```text
download_data.py
  ↓ 下載 raw CSV
build_parquet_dataset.py
  ↓ 正規化 raw CSV → Parquet
stock.duckdb
  ↓ 給 DBeaver 使用的 view file
query_stock_data.py
  ↓ 給 Agent 使用的查詢 CLI
```

原則：

- raw CSV 不修改，保留追溯來源。
- Parquet 是分析主資料。
- Agent 查詢不要依賴 `stock.duckdb`，避免 DBeaver 鎖檔。
- `stock.duckdb` 只放 views，實際資料在 Parquet。

## Dataset

| Dataset | 說明 |
|---|---|
| `price` | 每日行情，含 OHLCV、成交金額、成交筆數 |
| `margin` | 融資融券，含資買、資賣、資餘額、券餘額 |
| `day_trading` | 當沖量額 |
| `legal_person` | 三大法人買賣超，含外資、投信、自營商與合計 |
| `stock_list` | 上市/上櫃股票清單，含 ETF、創新板與 TDR |

## Download Raw CSV

下載腳本：

```text
scripts/download_data.py
```

下載單日全部資料：

```bash
python3 scripts/download_data.py --date 20260605 --type all --market all
```

下載日期區間：

```bash
python3 scripts/download_data.py --start 20260601 --end 20260605 --type all --market all --weekdays-only
```

只下載某一類：

```bash
python3 scripts/download_data.py --date 20260605 --type price
python3 scripts/download_data.py --date 20260605 --type margin
python3 scripts/download_data.py --date 20260605 --type day_trading
python3 scripts/download_data.py --date 20260605 --type legal_person
```

只下載某市場：

```bash
python3 scripts/download_data.py --date 20260605 --market twse
python3 scripts/download_data.py --date 20260605 --market tpex
```

常用參數：

```text
--root          StockResource 根目錄，預設 /Users/wellstseng/project/StockResource
--type          all / price / margin / day_trading / legal_person，可逗號分隔
--market        all / twse / tpex，可逗號分隔
--date          單日 YYYYMMDD
--start --end   日期區間 YYYYMMDD
--force         已有 CSV 也重抓
--dry-run       只顯示動作，不下載
--weekdays-only 跳過週末
```

## Build Parquet

轉檔腳本：

```text
scripts/build_parquet_dataset.py
```

全量轉檔：

```bash
python3 scripts/build_parquet_dataset.py --type all --verify
```

單日轉檔：

```bash
python3 scripts/build_parquet_dataset.py --date 20260605 --type all --verify
```

日期區間轉檔：

```bash
python3 scripts/build_parquet_dataset.py --start 20260601 --end 20260605 --type all --verify
```

只轉某一類：

```bash
python3 scripts/build_parquet_dataset.py --type price --date 20260605
python3 scripts/build_parquet_dataset.py --type margin --date 20260605
python3 scripts/build_parquet_dataset.py --type day_trading --date 20260605
python3 scripts/build_parquet_dataset.py --type legal_person --date 20260605
python3 scripts/build_parquet_dataset.py --type stock_list
```

常用參數：

```text
--root          StockResource 根目錄，預設 /Users/wellstseng/project/StockResource
--output        Parquet 輸出目錄，預設 <root>/parquet
--type          all / price / margin / day_trading / legal_person / stock_list，可逗號分隔
--market        all / twse / tpex，可逗號分隔
--date          單日 YYYYMMDD
--start --end   日期區間 YYYYMMDD
--force         已有 Parquet 也重轉
--dry-run       只顯示動作，不輸出
--verify        用 DuckDB 做 row count 驗證；本機需安裝 duckdb Python package
--fail-on-error 遇到壞檔時讓 process exit code = 1
```

轉檔結果：

```text
/Users/wellstseng/project/StockResource/parquet/
  price/
  margin/
  day_trading/
  legal_person/
  stock_list/
  _build_manifest.json
```

`_build_manifest.json` 會記錄 summary 與壞檔。

## Agent CLI

查 schema：

```bash
python3 scripts/query_stock_data.py schema --dataset all
```

查單表，預設 JSON：

```bash
python3 scripts/query_stock_data.py query --dataset price --symbol 2330 --limit 20
```

查日期區間：

```bash
python3 scripts/query_stock_data.py query --dataset price --symbol 2330 --start 20260101 --end 20260605
```

查 price + margin + day_trading join：

```bash
python3 scripts/query_stock_data.py joined --symbol 2330 --limit 20
```

查三大法人：

```bash
python3 scripts/query_stock_data.py query --dataset legal_person --symbol 2330 --limit 20
```

## Agent Technical Analysis

技術分析腳本：

```text
scripts/technical_analysis.py
```

查單股技術分析，預設 JSON：

```bash
python3 scripts/technical_analysis.py analyze --symbol 2330 --lookback 300
```

人看用 table：

```bash
python3 scripts/technical_analysis.py analyze --symbol 2330 --lookback 300 --format table
```

附最近 N 根含指標 K 線：

```bash
python3 scripts/technical_analysis.py analyze --symbol 2330 --lookback 300 --series-limit 5
```

全市場條件掃描：

```bash
python3 scripts/technical_analysis.py screen --preset breakout_20d --limit 20
python3 scripts/technical_analysis.py screen --preset ma_bullish_alignment --market twse --limit 20 --format table
python3 scripts/technical_analysis.py screen --preset rsi_oversold --sort rsi_14 --asc --limit 20
```

市場結構摘要：

```bash
python3 scripts/technical_analysis.py market-summary --limit 10
python3 scripts/technical_analysis.py market-summary --market twse --format table
```

目前支援：

- SMA：5、10、20、60、120、240
- EMA：12、26
- RSI：14
- MACD：12/26/9
- KD：9
- Bollinger Bands：20、2σ
- ATR：14
- volume MA：5、20
- 20/60 日支撐壓力、52 週高低
- 趨勢分類、常用訊號、資料 warnings

`screen --preset` 支援：

```text
breakout_20d
breakdown_20d
ma_bullish_alignment
ma_bearish_alignment
volume_surge
rsi_oversold
rsi_overbought
macd_bullish_cross
macd_bearish_cross
near_52w_high
near_52w_low
```

`market-summary` 會輸出：

- 漲跌家數與比例
- 站上 SMA20/SMA60/SMA240 比例
- 20 日突破/跌破數
- 爆量數
- 均線多頭/空頭排列數
- 漲幅、跌幅、爆量、突破、跌破排行

注意：

- 目前使用未復權價；跨除權息的長期均線與報酬率可能失真。
- 預設會排除單日疑似異常價，並在 `warnings` 標出日期；可用 `--no-filter-outliers` 關閉。
- 全市場掃描預設只納入指定日期當天仍有行情的標的；可用 `--include-stale` 納入停牌或當天無交易資料的標的。
- `--symbol-regex` 預設 `^[0-9]{4}$`，先聚焦 4 碼股票/TDR；如要 ETF 可自行放寬。
- `--adjusted` 目前會直接失敗，等 `corporate_actions` / `adjusted_price` 資料集補齊後再開。

## Agent Chip Analysis

籌碼分析腳本：

```text
scripts/chip_analysis.py
```

產出指定日期 JSON：

```bash
python3 scripts/chip_analysis.py --date 2026-06-05
```

預設輸出：

```text
/Users/wellstseng/project/StockResource/analysis/YYYY-MM-DD_chip_analysis.json
```

輸出內容：

- 三大法人總買賣超
- 外資 / 投信 / 自營買賣超排行
- 產業別法人資金流向
- 融資增減排行
- 當沖熱度排行
- 背離訊號：價漲外資賣超、價跌投信買超、融資大增但股價轉弱、當沖比過高風險

常用參數：

```text
--date                   YYYY-MM-DD / YYYYMMDD / latest
--limit                  各排行筆數，預設 20
--day-trade-risk-ratio   當沖比風險門檻，預設 30%
--output                 覆寫輸出路徑
```

直接執行 SQL：

```bash
python3 scripts/query_stock_data.py sql --query "select count(*) as rows from price"
```

查股票清單：

```bash
python3 scripts/query_stock_data.py query --dataset stock_list --where-sql "market = '上市'" --limit 20
```

用 table 格式給人看：

```bash
python3 scripts/query_stock_data.py joined --symbol 2330 --limit 5 --format table
```

輸出格式：

```text
--format json   # 預設，Agent 優先使用
--format jsonl
--format csv
--format table  # 人看用
```

常用參數：

```text
schema
  --dataset all / price / margin / day_trading / legal_person / stock_list

query
  --dataset      price / margin / day_trading / legal_person / stock_list
  --symbol       股票代號
  --market       all / twse / tpex
  --start --end  日期區間，YYYYMMDD 或 YYYY-MM-DD
  --columns      欄位清單，逗號分隔；預設 *
  --where-sql    額外 SQL 條件
  --limit        筆數限制，預設 100
  --format       json / jsonl / csv / table

joined
  以 price 為主，left join margin、day_trading 與 legal_person

sql
  --query        直接執行 SQL
  --file         從 .sql 檔讀 SQL
```

## Update DuckDB View File

DBeaver 使用的 `stock.duckdb` views 可用這支腳本更新：

```bash
python3 scripts/update_stock_duckdb.py
```

注意：DBeaver 開著時會鎖住 `stock.duckdb`，更新 view 前要先關掉 DBeaver 或 disconnect。

## DBeaver

DBeaver 可以連：

```text
/Users/wellstseng/project/StockResource/stock.duckdb
```

目前 `stock.duckdb` 裡是 views，不是實體 tables：

```text
main.price
main.margin
main.day_trading
main.legal_person
main.stock_list
```

在 DBeaver 左側需看：

```text
Schemas → main → Views
```

常用查詢：

```sql
select *
from price
where symbol = '2330'
order by date desc
limit 20;
```

```sql
select
  p.date,
  p.symbol,
  p.name,
  p.close,
  p.volume,
  m.margin_balance,
  m.short_balance,
  d.day_trade_volume,
  l.foreign_net,
  l.investment_trust_net,
  l.dealer_net,
  l.total_net
from price p
left join margin m
  on p.date = m.date and p.market = m.market and p.symbol = m.symbol
left join day_trading d
  on p.date = d.date and p.market = d.market and p.symbol = d.symbol
left join legal_person l
  on p.date = l.date and p.market = l.market and p.symbol = l.symbol
where p.symbol = '2330'
order by p.date desc
limit 20;
```

## Daily Update

每日更新建議流程：

```bash
python3 scripts/download_data.py --date 20260605 --type all --market all
python3 scripts/build_parquet_dataset.py --date 20260605 --type all --verify
python3 scripts/update_stock_duckdb.py
```

如果要補一段時間：

```bash
python3 scripts/download_data.py --start 20260601 --end 20260605 --type all --market all --weekdays-only
python3 scripts/build_parquet_dataset.py --start 20260601 --end 20260605 --type all --verify
python3 scripts/update_stock_duckdb.py
```

排程時建議：

- 先下載 raw CSV。
- 再轉同一天 Parquet。
- 用 `audit_local_data.py --types legal_person --freshness` 檢查法人資料日期是否跟 price 對齊。
- 加 `--verify` 檢查 row count。
- DBeaver 若需要看到新 view，關閉 DBeaver 後跑 `update_stock_duckdb.py`。
- 需要嚴格失敗才加 `--fail-on-error`。
- 不要每日全量重建；只有 schema/parser 修正時才全量重建。

## 注意事項

- `stock.duckdb` 很小是正常的，實際資料在 Parquet。
- DBeaver 開著時會鎖住 `stock.duckdb`；Agent 查詢請用 CLI。
- 全量 Parquet row count：

```text
price        92,243,859
margin        8,002,094
day_trading   4,005,899
legal_person      2,012  # 目前僅已匯入 2026-06-05 單日驗證資料
stock_list        2,322
```

- 2026-06-07 驗證：2026-06-05 最新行情中 1,965 個 4 碼可交易標的全數存在於 `stock_list`。
- `StockList/loader.py` 會同時輸出 `StockList/list_*.csv` 與 `/Users/wellstseng/project/StockResource/data/list*.csv`；更新清單後仍需重建 `stock_list` Parquet。

- 已知 raw CSV 壞檔：

```text
/Users/wellstseng/project/StockResource/data/day_trading/twse/20170519.csv
/Users/wellstseng/project/StockResource/data/day_trading/tpex/20150124.csv
```
