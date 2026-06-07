#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import csv
import json
import os
import re
from datetime import date, datetime
from io import StringIO
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


DEFAULT_ROOT = "/Users/wellstseng/project/StockResource"
DATA_TYPES = ("price", "margin", "day_trading", "stock_list")
MARKETS = ("twse", "tpex")
DATE_RE = re.compile(r"^\d{8}$")
SYMBOL_RE = re.compile(r"^[0-9A-Za-z]+$")


PRICE_SCHEMA = pa.schema([
    ("date", pa.date32()),
    ("market", pa.string()),
    ("symbol", pa.string()),
    ("name", pa.string()),
    ("open", pa.float64()),
    ("high", pa.float64()),
    ("low", pa.float64()),
    ("close", pa.float64()),
    ("volume", pa.int64()),
    ("amount", pa.int64()),
    ("transactions", pa.int64()),
    ("source_file", pa.string()),
])

MARGIN_SCHEMA = pa.schema([
    ("date", pa.date32()),
    ("market", pa.string()),
    ("symbol", pa.string()),
    ("name", pa.string()),
    ("margin_buy", pa.int64()),
    ("margin_sell", pa.int64()),
    ("margin_cash_repay", pa.int64()),
    ("margin_prev_balance", pa.int64()),
    ("margin_balance", pa.int64()),
    ("margin_limit", pa.int64()),
    ("short_buy", pa.int64()),
    ("short_sell", pa.int64()),
    ("short_stock_repay", pa.int64()),
    ("short_prev_balance", pa.int64()),
    ("short_balance", pa.int64()),
    ("short_limit", pa.int64()),
    ("offset", pa.int64()),
    ("note", pa.string()),
    ("source_file", pa.string()),
])

DAY_TRADING_SCHEMA = pa.schema([
    ("date", pa.date32()),
    ("market", pa.string()),
    ("symbol", pa.string()),
    ("name", pa.string()),
    ("suspend_note", pa.string()),
    ("day_trade_volume", pa.int64()),
    ("day_trade_buy_amount", pa.int64()),
    ("day_trade_sell_amount", pa.int64()),
    ("source_file", pa.string()),
])

STOCK_LIST_SCHEMA = pa.schema([
    ("symbol", pa.string()),
    ("name", pa.string()),
    ("listing_date", pa.date32()),
    ("market", pa.string()),
    ("industry", pa.string()),
    ("source_file", pa.string()),
])


def parse_ymd(value):
    return datetime.strptime(value, "%Y%m%d").date()


def parse_slash_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value.strip(), "%Y/%m/%d").date()
    except ValueError:
        return None


def ymd(value):
    return value.strftime("%Y%m%d")


def selected(value, all_values):
    if value == "all":
        return list(all_values)
    result = [i.strip() for i in value.split(",") if i.strip()]
    bad = sorted(set(result) - set(all_values))
    if bad:
        raise SystemExit("bad value: {0}".format(",".join(bad)))
    return result


def clean_cell(value):
    value = value.strip()
    if value.startswith("="):
        value = value[1:].strip()
    return value.strip()


def parse_int(value):
    value = clean_cell(value).replace(",", "").replace("%", "")
    if value in ("", "--", "---", "N/A", "NA"):
        return None
    if value.startswith("(") and value.endswith(")"):
        value = "-" + value[1:-1]
    try:
        return int(float(value))
    except ValueError:
        return None


def parse_float(value):
    value = clean_cell(value).replace(",", "")
    if value in ("", "--", "---", "N/A", "NA"):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def is_symbol(value):
    value = clean_cell(value)
    return bool(value) and bool(SYMBOL_RE.match(value))


def read_csv_rows(path):
    data = path.read_bytes()
    if not data:
        raise ValueError("empty_file")
    if set(data) == {0}:
        raise ValueError("all_zero_file")

    data = data.replace(b"\x00", b"")
    for encoding in ("utf-8-sig", "cp950", "big5"):
        try:
            text = data.decode(encoding)
            break
        except UnicodeDecodeError:
            text = None
    if text is None:
        text = data.decode("utf-8", errors="replace")

    rows = []
    for row in csv.reader(StringIO(text, newline="")):
        clean = [clean_cell(i) for i in row]
        if any(clean):
            rows.append(clean)
    return rows


def find_header(rows, candidates):
    for index, row in enumerate(rows):
        if len(row) >= 2 and row[0] in candidates and row[1] in ("證券名稱", "名稱", "股票名稱"):
            return index, row
    return None, None


def by_header(header, row, names):
    for name in names:
        if name in header:
            index = header.index(name)
            if index < len(row):
                return row[index]
    return ""


def parse_price(path, market, value):
    rows = read_csv_rows(path)
    header_index, header = find_header(rows, ("證券代號", "代號"))
    if header is None:
        raise ValueError("price_header_not_found")

    records = []
    for row in rows[header_index + 1:]:
        symbol = by_header(header, row, ("證券代號", "代號"))
        if not is_symbol(symbol):
            continue
        records.append({
            "date": value,
            "market": market,
            "symbol": clean_cell(symbol),
            "name": by_header(header, row, ("證券名稱", "名稱")),
            "open": parse_float(by_header(header, row, ("開盤價", "開盤"))),
            "high": parse_float(by_header(header, row, ("最高價", "最高"))),
            "low": parse_float(by_header(header, row, ("最低價", "最低"))),
            "close": parse_float(by_header(header, row, ("收盤價", "收盤"))),
            "volume": parse_int(by_header(header, row, ("成交股數",))),
            "amount": parse_int(by_header(header, row, ("成交金額", "成交金額(元)"))),
            "transactions": parse_int(by_header(header, row, ("成交筆數",))),
            "source_file": str(path),
        })
    return records


def parse_margin(path, market, value):
    rows = read_csv_rows(path)
    header_index, header = find_header(rows, ("代號", "股票代號"))
    if header is None:
        raise ValueError("margin_header_not_found")

    records = []
    for row in rows[header_index + 1:]:
        if len(row) < 2 or not is_symbol(row[0]):
            continue

        if market == "tpex":
            record = {
                "margin_prev_balance": parse_int(row[2] if len(row) > 2 else ""),
                "margin_buy": parse_int(row[3] if len(row) > 3 else ""),
                "margin_sell": parse_int(row[4] if len(row) > 4 else ""),
                "margin_cash_repay": parse_int(row[5] if len(row) > 5 else ""),
                "margin_balance": parse_int(row[6] if len(row) > 6 else ""),
                "margin_limit": parse_int(row[9] if len(row) > 9 else ""),
                "short_prev_balance": parse_int(row[10] if len(row) > 10 else ""),
                "short_sell": parse_int(row[11] if len(row) > 11 else ""),
                "short_buy": parse_int(row[12] if len(row) > 12 else ""),
                "short_stock_repay": parse_int(row[13] if len(row) > 13 else ""),
                "short_balance": parse_int(row[14] if len(row) > 14 else ""),
                "short_limit": parse_int(row[17] if len(row) > 17 else ""),
                "offset": parse_int(row[18] if len(row) > 18 else ""),
                "note": row[19] if len(row) > 19 else "",
            }
        else:
            record = {
                "margin_buy": parse_int(row[2] if len(row) > 2 else ""),
                "margin_sell": parse_int(row[3] if len(row) > 3 else ""),
                "margin_cash_repay": parse_int(row[4] if len(row) > 4 else ""),
                "margin_prev_balance": parse_int(row[5] if len(row) > 5 else ""),
                "margin_balance": parse_int(row[6] if len(row) > 6 else ""),
                "margin_limit": parse_int(row[7] if len(row) > 7 else ""),
                "short_buy": parse_int(row[8] if len(row) > 8 else ""),
                "short_sell": parse_int(row[9] if len(row) > 9 else ""),
                "short_stock_repay": parse_int(row[10] if len(row) > 10 else ""),
                "short_prev_balance": parse_int(row[11] if len(row) > 11 else ""),
                "short_balance": parse_int(row[12] if len(row) > 12 else ""),
                "short_limit": parse_int(row[13] if len(row) > 13 else ""),
                "offset": parse_int(row[14] if len(row) > 14 else ""),
                "note": row[15] if len(row) > 15 else "",
            }

        record.update({
            "date": value,
            "market": market,
            "symbol": clean_cell(row[0]),
            "name": row[1],
            "source_file": str(path),
        })
        records.append(record)
    return records


def parse_day_trading(path, market, value):
    rows = read_csv_rows(path)
    header_index, header = find_header(rows, ("證券代號", "代號"))
    if header is None:
        raise ValueError("day_trading_header_not_found")

    records = []
    for row in rows[header_index + 1:]:
        if len(row) < 2 or not is_symbol(row[0]):
            continue
        records.append({
            "date": value,
            "market": market,
            "symbol": clean_cell(row[0]),
            "name": row[1],
            "suspend_note": row[2] if len(row) > 2 else "",
            "day_trade_volume": parse_int(row[3] if len(row) > 3 else ""),
            "day_trade_buy_amount": parse_int(row[4] if len(row) > 4 else ""),
            "day_trade_sell_amount": parse_int(row[5] if len(row) > 5 else ""),
            "source_file": str(path),
        })
    return records


def parse_stock_list(path):
    rows = read_csv_rows(path)
    if not rows:
        return []
    header = rows[0]
    records = []
    for row in rows[1:]:
        symbol = by_header(header, row, ("id",))
        if not is_symbol(symbol):
            continue
        records.append({
            "symbol": clean_cell(symbol),
            "name": by_header(header, row, ("name",)),
            "listing_date": parse_slash_date(by_header(header, row, ("listing_date",))),
            "market": by_header(header, row, ("market",)),
            "industry": by_header(header, row, ("industry",)),
            "source_file": str(path),
        })
    return records


def schema_for(dtype):
    return {
        "price": PRICE_SCHEMA,
        "margin": MARGIN_SCHEMA,
        "day_trading": DAY_TRADING_SCHEMA,
        "stock_list": STOCK_LIST_SCHEMA,
    }[dtype]


def parser_for(dtype):
    return {
        "price": parse_price,
        "margin": parse_margin,
        "day_trading": parse_day_trading,
    }[dtype]


def write_records(records, schema, target, force, dry_run):
    if dry_run:
        return
    if target.exists() and not force:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(records, schema=schema)
    pq.write_table(table, target, compression="zstd")


def build_data_type(root, output, dtype, markets, start, end, force, dry_run):
    summary = {}
    errors = []
    parser = parser_for(dtype)

    for market in markets:
        src_dir = root / "data" / dtype / market
        files = sorted(src_dir.glob("*.csv")) if src_dir.exists() else []
        for path in files:
            if not DATE_RE.match(path.stem):
                continue
            value = parse_ymd(path.stem)
            if start and value < start:
                continue
            if end and value > end:
                continue

            target = output / dtype / "market-{0}".format(market) / "year-{0}".format(value.year) / "{0}.parquet".format(path.stem)
            if target.exists() and not force:
                summary[(dtype, market, "exists")] = summary.get((dtype, market, "exists"), 0) + 1
                continue

            try:
                records = parser(path, market, value)
                write_records(records, schema_for(dtype), target, force, dry_run)
                summary[(dtype, market, "ok")] = summary.get((dtype, market, "ok"), 0) + 1
                summary[(dtype, market, "rows")] = summary.get((dtype, market, "rows"), 0) + len(records)
            except Exception as exc:
                errors.append({"type": dtype, "market": market, "date": path.stem, "file": str(path), "error": str(exc)})
                summary[(dtype, market, "error")] = summary.get((dtype, market, "error"), 0) + 1
    return summary, errors


def build_stock_list(root, output, force, dry_run):
    summary = {}
    errors = []
    for name in ("list2.csv", "list4.csv"):
        path = root / "data" / name
        if not path.exists():
            continue
        target = output / "stock_list" / "{0}.parquet".format(path.stem)
        if target.exists() and not force:
            summary[("stock_list", path.stem, "exists")] = 1
            continue
        try:
            records = parse_stock_list(path)
            write_records(records, STOCK_LIST_SCHEMA, target, force, dry_run)
            summary[("stock_list", path.stem, "ok")] = 1
            summary[("stock_list", path.stem, "rows")] = len(records)
        except Exception as exc:
            errors.append({"type": "stock_list", "file": str(path), "error": str(exc)})
            summary[("stock_list", path.stem, "error")] = 1
    return summary, errors


def merge_summary(target, source):
    for key, value in source.items():
        target[key] = target.get(key, 0) + value


def write_manifest(output, summary, errors, dry_run):
    if dry_run:
        return
    output.mkdir(parents=True, exist_ok=True)
    manifest = {
        "built_at": datetime.now().isoformat(timespec="seconds"),
        "summary": [{"key": list(key), "value": value} for key, value in sorted(summary.items())],
        "errors": errors,
    }
    with (output / "_build_manifest.json").open("w", encoding="utf8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


def verify_with_duckdb(output):
    import glob

    try:
        import duckdb
    except ImportError:
        print("VERIFY duckdb=missing skip")
        return

    con = duckdb.connect()
    for dtype in ("price", "margin", "day_trading"):
        pattern = str(output / dtype / "**" / "*.parquet")
        if not glob.glob(pattern, recursive=True):
            continue
        count = con.execute("select count(*) from read_parquet(?)", [pattern]).fetchone()[0]
        print("VERIFY {0} rows={1}".format(dtype, count))
    stock_pattern = str(output / "stock_list" / "*.parquet")
    if not glob.glob(stock_pattern):
        return
    count = con.execute("select count(*) from read_parquet(?)", [stock_pattern]).fetchone()[0]
    print("VERIFY stock_list rows={0}".format(count))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=os.environ.get("STOCK_RESOURCE_PATH", DEFAULT_ROOT))
    parser.add_argument("--output")
    parser.add_argument("--type", default="all", help="all or comma-separated: price,margin,day_trading,stock_list")
    parser.add_argument("--market", default="all", help="all or comma-separated: twse,tpex")
    parser.add_argument("--date", help="YYYYMMDD. Ignored when --start is used")
    parser.add_argument("--start", help="YYYYMMDD")
    parser.add_argument("--end", help="YYYYMMDD")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verify", action="store_true", help="run DuckDB row-count checks when duckdb is installed")
    parser.add_argument("--fail-on-error", action="store_true")
    args = parser.parse_args()

    root = Path(args.root)
    output = Path(args.output) if args.output else root / "parquet"
    dtypes = selected(args.type, DATA_TYPES)
    markets = selected(args.market, MARKETS)

    start = parse_ymd(args.start) if args.start else None
    end = parse_ymd(args.end) if args.end else None
    if args.date and not start:
        start = parse_ymd(args.date)
        end = start
    if start and end and end < start:
        raise SystemExit("--end must be >= --start")

    summary = {}
    errors = []
    for dtype in dtypes:
        if dtype == "stock_list":
            part_summary, part_errors = build_stock_list(root, output, args.force, args.dry_run)
        else:
            part_summary, part_errors = build_data_type(root, output, dtype, markets, start, end, args.force, args.dry_run)
        merge_summary(summary, part_summary)
        errors.extend(part_errors)

    write_manifest(output, summary, errors, args.dry_run)
    for key, value in sorted(summary.items()):
        print("{0}={1}".format("/".join(key), value))
    if errors:
        print("ERRORS {0} see {1}".format(len(errors), output / "_build_manifest.json"))
    if args.verify and not args.dry_run:
        verify_with_duckdb(output)
    return 1 if errors and args.fail_on_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
