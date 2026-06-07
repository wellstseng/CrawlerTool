#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import os
import re
from datetime import date, datetime
from pathlib import Path


DEFAULT_ROOT = "/Users/wellstseng/project/StockResource"
DATA_TYPES = ("price", "margin", "day_trading", "legal_person")
MARKETS = ("twse", "tpex")
DATE_RE = re.compile(r"^\d{8}$")


def parse_ymd(value):
    return datetime.strptime(value, "%Y%m%d").date()


def ymd(value):
    return value.strftime("%Y%m%d")


def load_no_data(root):
    path = Path(root) / "data" / "_backfill_aux_state.json"
    if not path.exists():
        return {}
    with path.open("r", encoding="utf8") as f:
        data = json.load(f)
    return {key: set(value.get("no_data", [])) for key, value in data.items()}


def scan_bucket(root, dtype, market):
    path = Path(root) / "data" / dtype / market
    files = set()
    invalid = []
    weekend = []
    if not path.exists():
        return files, [("missing_dir", str(path))], weekend

    for item in path.iterdir():
        if not item.is_file() or item.suffix.lower() != ".csv":
            continue
        stem = item.stem
        if not DATE_RE.match(stem):
            invalid.append(("bad_name", item.name))
            continue
        try:
            value = parse_ymd(stem)
        except ValueError:
            invalid.append(("bad_date", item.name))
            continue
        files.add(stem)
        if value.weekday() >= 5:
            weekend.append(stem)
    return files, invalid, weekend


def clamp_dates(values, start, end):
    result = set()
    for value in values:
        dt = parse_ymd(value)
        if start <= dt <= end and dt.weekday() < 5:
            result.add(value)
    return result


def summarize_dates(values):
    if not values:
        return "count=0"
    items = sorted(values)
    return "count={0} first={1} last={2}".format(len(items), items[0], items[-1])


def sample(values, limit):
    items = sorted(values)
    if len(items) <= limit * 2:
        return ",".join(items)
    return "{0} ... {1}".format(",".join(items[:limit]), ",".join(items[-limit:]))


def active_start(files, explicit_start):
    if explicit_start is not None:
        return explicit_start
    if not files:
        return None
    return parse_ymd(min(files))


def print_freshness(scanned, dtypes, markets):
    print("== freshness ==")
    for market in markets:
        price_files = scanned.get(("price", market), {}).get("files", set())
        price_latest = max(price_files) if price_files else None
        for dtype in dtypes:
            files = scanned.get((dtype, market), {}).get("files", set())
            latest = max(files) if files else None
            lag_days = None
            stale = None
            if price_latest and latest:
                lag_days = (parse_ymd(price_latest) - parse_ymd(latest)).days
                stale = latest < price_latest
            elif price_latest and not latest:
                stale = True
            print(
                "{dtype}/{market} latest={latest} price_latest={price_latest} lag_days={lag_days} stale={stale}".format(
                    dtype=dtype,
                    market=market,
                    latest=latest or "-",
                    price_latest=price_latest or "-",
                    lag_days="-" if lag_days is None else lag_days,
                    stale="-" if stale is None else stale,
                )
            )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=os.environ.get("STOCK_RESOURCE_PATH", DEFAULT_ROOT))
    parser.add_argument("--types", default=",".join(DATA_TYPES), help="comma-separated: price,margin,day_trading,legal_person")
    parser.add_argument("--markets", default=",".join(MARKETS), help="comma-separated: twse,tpex")
    parser.add_argument("--start", help="YYYYMMDD. Default: each bucket's first local CSV date")
    parser.add_argument("--end", default=date.today().strftime("%Y%m%d"))
    parser.add_argument("--sample", type=int, default=8)
    parser.add_argument("--show-missing", action="store_true")
    parser.add_argument(
        "--expected-source",
        choices=("price", "inferred"),
        default="price",
        help="use local price as aux trading-day baseline; for price, also report tail gaps from other local data types. inferred uses same data type only",
    )
    parser.add_argument("--strict-weekdays", action="store_true", help="expect every weekday instead of inferred local trading days")
    parser.add_argument("--freshness", action="store_true", help="print latest local CSV date per type/market compared with price")
    parser.add_argument("--fail-on-missing", action="store_true")
    args = parser.parse_args()

    dtypes = [i.strip() for i in args.types.split(",") if i.strip()]
    markets = [i.strip() for i in args.markets.split(",") if i.strip()]
    bad_types = sorted(set(dtypes) - set(DATA_TYPES))
    bad_markets = sorted(set(markets) - set(MARKETS))
    if bad_types or bad_markets:
        raise SystemExit("bad types={0} markets={1}".format(bad_types, bad_markets))

    explicit_start = parse_ymd(args.start) if args.start else None
    end = parse_ymd(args.end)
    no_data = load_no_data(args.root)

    scan_types = set(dtypes)
    if args.expected_source == "price":
        if "price" in dtypes:
            scan_types.update(DATA_TYPES)
        if any(dtype != "price" for dtype in dtypes):
            scan_types.add("price")

    scanned = {}
    for dtype in scan_types:
        for market in markets:
            files, invalid, weekend = scan_bucket(args.root, dtype, market)
            scanned[(dtype, market)] = {
                "files": files,
                "invalid": invalid,
                "weekend": weekend,
            }

    has_missing = False
    for dtype in dtypes:
        print("== {0} ==".format(dtype))
        dtype_dates = set()
        if dtype == "price" or args.expected_source == "inferred":
            for market in markets:
                key = (dtype, market)
                start = active_start(scanned[key]["files"], explicit_start)
                if start is None:
                    continue
                dtype_dates |= clamp_dates(scanned[key]["files"], start, end)
                dtype_dates |= clamp_dates(no_data.get("{0}/{1}".format(dtype, market), set()), start, end)

        if args.strict_weekdays:
            cursor = explicit_start
            if cursor is None:
                starts = [active_start(scanned[(dtype, m)]["files"], None) for m in markets]
                starts = [i for i in starts if i is not None]
                cursor = min(starts) if starts else end
            dtype_dates = set()
            while cursor <= end:
                if cursor.weekday() < 5:
                    dtype_dates.add(ymd(cursor))
                cursor = date.fromordinal(cursor.toordinal() + 1)

        for market in markets:
            key = (dtype, market)
            files = scanned[key]["files"]
            start = active_start(files, explicit_start)
            if start is None:
                print("{0} files=0 missing=NO_LOCAL_FILES".format(market))
                has_missing = True
                continue

            if dtype != "price" and args.expected_source == "price" and not args.strict_weekdays:
                price_files = scanned.get(("price", market), {}).get("files", set())
                expected = clamp_dates(price_files, start, end)
            else:
                expected = {i for i in dtype_dates if start <= parse_ymd(i) <= end}
            known_no_data = no_data.get("{0}/{1}".format(dtype, market), set())
            missing = sorted(expected - files - known_no_data)
            tail_missing = []
            if dtype == "price" and args.expected_source == "price" and not args.strict_weekdays:
                clue_dates = set()
                for source_type in scan_types:
                    bucket = scanned.get((source_type, market))
                    if bucket is None:
                        continue
                    clue_dates |= clamp_dates(bucket["files"], start, end)
                tail_missing = sorted(i for i in clue_dates if i > max(files) and i not in files)
            invalid = scanned[key]["invalid"]
            weekend = sorted(scanned[key]["weekend"])
            has_missing = has_missing or bool(missing) or bool(tail_missing)

            print(
                "{market} files={files} expected={expected} missing={missing} tail_missing={tail_missing} first={first} last={last} no_data={no_data} invalid={invalid} weekend_files={weekend}".format(
                    market=market,
                    files=len(files),
                    expected=len(expected),
                    missing=len(missing),
                    tail_missing=len(tail_missing),
                    first=min(files) if files else "-",
                    last=max(files) if files else "-",
                    no_data=len(known_no_data),
                    invalid=len(invalid),
                    weekend=len(weekend),
                )
            )
            if missing and (args.show_missing or args.sample > 0):
                print("  missing_sample={0}".format(sample(missing, args.sample)))
            if tail_missing and (args.show_missing or args.sample > 0):
                print("  tail_missing_sample={0}".format(sample(tail_missing, args.sample)))
            if invalid:
                print("  invalid_sample={0}".format(invalid[:args.sample]))
            if weekend:
                print("  weekend_sample={0}".format(sample(weekend, args.sample)))

    if args.freshness:
        print_freshness(scanned, dtypes, markets)
    if args.fail_on_missing and has_missing:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
