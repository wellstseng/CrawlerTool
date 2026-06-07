#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path


DEFAULT_ROOT = "/Users/wellstseng/project/StockResource"
DATA_TYPES = ("price", "margin", "day_trading")
MARKETS = ("twse", "tpex")


def parse_date(value):
    return datetime.strptime(value, "%Y%m%d").date()


def ymd(value):
    return value.strftime("%Y%m%d")


def slash_date(value):
    return value.strftime("%Y/%m/%d")


def iter_dates(start, end):
    cursor = start
    while cursor <= end:
        yield cursor
        cursor += timedelta(days=1)


def selected(values, all_values):
    if values == "all":
        return list(all_values)
    result = [i.strip() for i in values.split(",") if i.strip()]
    bad = sorted(set(result) - set(all_values))
    if bad:
        raise SystemExit("bad value: {0}".format(",".join(bad)))
    return result


def price_path(define, market, value):
    return Path(define.Define.DAILY_PRICE_FMT.format(market, ymd(value)))


def aux_path(backfill_aux, root, dtype, market, value):
    return backfill_aux.data_path(root, dtype, market, value)


def download_price(define, daily_price2, market, value, force):
    target = price_path(define, market, value)
    if force and target.exists():
        target.unlink()

    url = define.Define.TWSE_DAILY_PRICE_URL_FMT
    headers = define.Define.TWSE_DAILY_PRICE_HEADERS
    if market == define.MarketType.TPEX:
        url = define.Define.TPEX_DAILY_PRICE_URL_FMT
        headers = define.Define.TPEX_DAILY_PRICE_HEADERS

    daily_price2.load_range(
        market,
        url,
        headers,
        start_date=slash_date(value),
        end_date=slash_date(value - timedelta(days=1)),
        parse_to_db=False,
        try_load=True,
    )

    if target.exists():
        return ("OK", ymd(value), str(target))
    return ("NO_DATA", ymd(value), str(target))


def download_aux(backfill_aux, root, dtype, market, value, force, timeout, dry_run):
    target = aux_path(backfill_aux, root, dtype, market, value)
    if force and target.exists() and not dry_run:
        target.unlink()
    if target.exists() and not force:
        return ("EXISTS", ymd(value), str(target))

    url_fmt = backfill_aux.TASKS[(dtype, market)]
    result = backfill_aux.fetch_one(root, dtype, market, url_fmt, value, timeout, dry_run)
    if result[0] == "OK" and target.exists():
        return ("OK", ymd(value), str(target))
    return (result[0], result[1], result[3] if len(result) > 3 and result[3] else str(target))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=os.environ.get("STOCK_RESOURCE_PATH", DEFAULT_ROOT))
    parser.add_argument("--type", default="all", help="all or comma-separated: price,margin,day_trading")
    parser.add_argument("--market", default="all", help="all or comma-separated: twse,tpex")
    parser.add_argument("--date", default=date.today().strftime("%Y%m%d"), help="YYYYMMDD. Ignored when --start is used")
    parser.add_argument("--start", help="YYYYMMDD")
    parser.add_argument("--end", help="YYYYMMDD")
    parser.add_argument("--force", action="store_true", help="re-download even when local CSV exists")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--weekdays-only", action="store_true")
    parser.add_argument("--sleep", type=float, default=1.0)
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()

    start = parse_date(args.start) if args.start else parse_date(args.date)
    end = parse_date(args.end) if args.end else start
    if end < start:
        raise SystemExit("--end must be >= --start")

    dtypes = selected(args.type, DATA_TYPES)
    markets = selected(args.market, MARKETS)

    os.environ["STOCK_RESOURCE_PATH"] = args.root
    sys.path.append(str(Path(__file__).resolve().parents[1]))

    import define
    from DailyTrade import daily_price2
    import backfill_aux

    counts = {}
    for value in iter_dates(start, end):
        if args.weekdays_only and value.weekday() >= 5:
            print("SKIP weekend {0}".format(ymd(value)), flush=True)
            continue

        for dtype in dtypes:
            for market in markets:
                if args.dry_run:
                    result = ("DRY_RUN", ymd(value), "{0}/{1}".format(dtype, market))
                elif dtype == "price":
                    result = download_price(define, daily_price2, market, value, args.force)
                else:
                    result = download_aux(backfill_aux, args.root, dtype, market, value, args.force, args.timeout, args.dry_run)

                counts[(dtype, market, result[0])] = counts.get((dtype, market, result[0]), 0) + 1
                print("{0}/{1} {2}".format(dtype, market, result), flush=True)

                if result[0] in ("REDIRECT", "RATE_LIMIT"):
                    print("STOP {0}/{1} status={2}".format(dtype, market, result[0]), flush=True)
                    print("SUMMARY {0}".format(sorted(counts.items())), flush=True)
                    return 2

                if args.sleep > 0:
                    time.sleep(args.sleep)

    print("SUMMARY {0}".format(sorted(counts.items())), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
