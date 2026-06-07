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
| `stock_list` | 上市/上櫃股票清單 |

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
```

只下載某市場：

```bash
python3 scripts/download_data.py --date 20260605 --market twse
python3 scripts/download_data.py --date 20260605 --market tpex
```

常用參數：

```text
--root          StockResource 根目錄，預設 /Users/wellstseng/project/StockResource
--type          all / price / margin / day_trading，可逗號分隔
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
python3 scripts/build_parquet_dataset.py --type stock_list
```

常用參數：

```text
--root          StockResource 根目錄，預設 /Users/wellstseng/project/StockResource
--output        Parquet 輸出目錄，預設 <root>/parquet
--type          all / price / margin / day_trading / stock_list，可逗號分隔
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
  --dataset all / price / margin / day_trading / stock_list

query
  --dataset      price / margin / day_trading / stock_list
  --symbol       股票代號
  --market       all / twse / tpex
  --start --end  日期區間，YYYYMMDD 或 YYYY-MM-DD
  --columns      欄位清單，逗號分隔；預設 *
  --where-sql    額外 SQL 條件
  --limit        筆數限制，預設 100
  --format       json / jsonl / csv / table

joined
  以 price 為主，left join margin 與 day_trading

sql
  --query        直接執行 SQL
  --file         從 .sql 檔讀 SQL
```

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
  d.day_trade_volume
from price p
left join margin m
  on p.date = m.date and p.market = m.market and p.symbol = m.symbol
left join day_trading d
  on p.date = d.date and p.market = d.market and p.symbol = d.symbol
where p.symbol = '2330'
order by p.date desc
limit 20;
```

## Daily Update

每日更新建議流程：

```bash
python3 scripts/download_data.py --date 20260605 --type all --market all
python3 scripts/build_parquet_dataset.py --date 20260605 --type all --verify
```

如果要補一段時間：

```bash
python3 scripts/download_data.py --start 20260601 --end 20260605 --type all --market all --weekdays-only
python3 scripts/build_parquet_dataset.py --start 20260601 --end 20260605 --type all --verify
```

排程時建議：

- 先下載 raw CSV。
- 再轉同一天 Parquet。
- 加 `--verify` 檢查 row count。
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
stock_list        1,744
```

- 已知 raw CSV 壞檔：

```text
/Users/wellstseng/project/StockResource/data/day_trading/twse/20170519.csv
/Users/wellstseng/project/StockResource/data/day_trading/tpex/20150124.csv
```
