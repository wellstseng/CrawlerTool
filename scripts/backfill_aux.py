#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import os
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import requests

sys.path.append(str(Path(__file__).resolve().parents[1]))

import define


DEFAULT_ROOT = "/Users/wellstseng/project/StockResource"
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "text/csv,*/*"}

TASKS = {
    ("margin", define.MarketType.TWSE): define.Define.TWSE_MARGIN_URL_FMT,
    ("margin", define.MarketType.TPEX): define.Define.TPEX_MARGIN_URL_FMT,
    ("day_trading", define.MarketType.TWSE): (
        define.Define.TWSE_DAYTRADING_URL_FMT,
        "https://www.twse.com.tw/rwd/zh/dayTrading/TWTB4U?date={0}&selectType=All&response=csv",
    ),
    ("day_trading", define.MarketType.TPEX): define.Define.TPEX_DAYTRADING_URL_FMT,
    ("legal_person", define.MarketType.TWSE): define.Define.TWSE_LEGAL_PERSON_TRADE_FMT,
    ("legal_person", define.MarketType.TPEX): define.Define.TPEX_LEGAL_PERSON_TRADE_FMT,
}


def parse_date(value):
    return datetime.strptime(value, "%Y%m%d").date()


def ymd(value):
    return value.strftime("%Y%m%d")


def roc_date(value):
    return "{0}/{1:02d}/{2:02d}".format(value.year - 1911, value.month, value.day)


def twse_text_date(value):
    return "{0}年{1:02d}月{2:02d}日".format(value.year - 1911, value.month, value.day)


def src_date(market, value):
    return roc_date(value) if market == define.MarketType.TPEX else ymd(value)


def iter_weekdays(start, end):
    cursor = end
    while cursor >= start:
        if cursor.weekday() < 5:
            yield cursor
        cursor -= timedelta(days=1)


def load_state(path):
    if not path.exists():
        return {}
    with path.open("r", encoding="utf8") as f:
        return json.load(f)


def save_state(path, state):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2, sort_keys=True)
    tmp_path.replace(path)


def task_key(dtype, market):
    return "{0}/{1}".format(dtype, market)


def is_known_no_data(state, dtype, market, value):
    return ymd(value) in state.get(task_key(dtype, market), {}).get("no_data", [])


def mark_no_data(state, dtype, market, value):
    key = task_key(dtype, market)
    bucket = state.setdefault(key, {}).setdefault("no_data", [])
    value = ymd(value)
    if value not in bucket:
        bucket.append(value)
        bucket.sort()


def response_is_data(dtype, market, value, text):
    if not text.strip() or "沒有符合條件的資料" in text:
        return False

    if market == define.MarketType.TPEX:
        if dtype == "margin":
            return (
                "資料日期:{0}".format(roc_date(value)) in text
                and "共0筆" not in text
                and "\"代號\"" in text
            )
        if dtype == "day_trading":
            return roc_date(value) in text and "\"證券代號\"" in text and len(text.splitlines()) > 6
        if dtype == "legal_person":
            return twse_text_date(value) in text and "三大法人" in text and "代號" in text and len(text.splitlines()) > 3

    if twse_text_date(value) not in text:
        return False
    if dtype == "margin":
        return "融資融券彙總" in text and "\"代號\"" in text and len(text.splitlines()) > 8
    if dtype == "day_trading":
        return "\"證券代號\"" in text and len(text.splitlines()) > 6
    if dtype == "legal_person":
        return "三大法人" in text and "\"證券代號\"" in text and len(text.splitlines()) > 3
    return False


def data_path(root, dtype, market, value):
    return Path(root) / "data" / dtype / market / (ymd(value) + ".csv")


def missing_dates(root, state, dtype, market, start, end, limit):
    result = []
    for value in iter_weekdays(start, end):
        if is_known_no_data(state, dtype, market, value):
            continue
        if data_path(root, dtype, market, value).exists():
            continue
        result.append(value)
        if len(result) >= limit:
            break
    return result


def fetch_one(root, dtype, market, url_fmt, value, timeout, dry_run):
    target = data_path(root, dtype, market, value)
    if dry_run:
        return ("DRY_RUN", ymd(value), "", "")

    url_formats = url_fmt if isinstance(url_fmt, tuple) else (url_fmt,)
    last_no_data = ("NO_DATA", ymd(value), 0, "")
    saw_wrong_date = False

    for one_url_fmt in url_formats:
        response = requests.get(
            one_url_fmt.format(src_date(market, value)),
            headers=HEADERS,
            timeout=timeout,
            allow_redirects=False,
        )
        if response.status_code in (301, 302, 303, 307, 308):
            return ("REDIRECT", ymd(value), response.status_code, response.headers.get("Location", ""))
        if response.status_code == 429:
            return ("RATE_LIMIT", ymd(value), 429, "")
        response.raise_for_status()

        text = response.content.decode("ms950", errors="replace")
        if not text.strip() or "沒有符合條件的資料" in text or "查詢日期" in text:
            last_no_data = ("NO_DATA", ymd(value), len(text), "")
            continue
        if text.strip() and market == define.MarketType.TWSE and twse_text_date(value) not in text:
            saw_wrong_date = True
            continue
        if not response_is_data(dtype, market, value, text):
            last_no_data = ("NO_DATA", ymd(value), len(text), "")
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf8", newline="") as f:
            f.write(text)
        return ("OK", ymd(value), len(text), "")

    if saw_wrong_date and last_no_data[2] == 0:
        return ("WRONG_DATE", ymd(value), 0, "")
    return last_no_data


def selected_tasks(dtype, market):
    result = []
    for key, url in TASKS.items():
        task_dtype, task_market = key
        if dtype != "all" and dtype != task_dtype:
            continue
        if market != "all" and market != task_market:
            continue
        result.append((task_dtype, task_market, url))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=os.environ.get("STOCK_RESOURCE_PATH", DEFAULT_ROOT))
    parser.add_argument("--type", choices=("margin", "day_trading", "legal_person", "all"), default="all")
    parser.add_argument("--market", choices=(define.MarketType.TWSE, define.MarketType.TPEX, "all"), default="all")
    parser.add_argument("--start", default="20180921")
    parser.add_argument("--end", default=date.today().strftime("%Y%m%d"))
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--sleep", type=float, default=2.0)
    parser.add_argument("--cooldown", type=float, default=60.0)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root = args.root
    state_path = Path(root) / "data" / "_backfill_aux_state.json"
    state = load_state(state_path)
    start = parse_date(args.start)
    end = parse_date(args.end)
    counts = {}

    for dtype, market, url_fmt in selected_tasks(args.type, args.market):
        key = task_key(dtype, market)
        dates = missing_dates(root, state, dtype, market, start, end, args.limit)
        if not dates:
            print("{0} NO_MISSING".format(key), flush=True)
            continue

        print("{0} START dates={1}".format(key, ",".join(ymd(i) for i in dates)), flush=True)
        for value in dates:
            try:
                result = fetch_one(root, dtype, market, url_fmt, value, args.timeout, args.dry_run)
            except Exception as ex:
                result = ("FAIL", ymd(value), type(ex).__name__, str(ex))

            status = result[0]
            counts[(key, status)] = counts.get((key, status), 0) + 1
            print("{0} {1}".format(key, result), flush=True)

            if status == "NO_DATA":
                mark_no_data(state, dtype, market, value)
                save_state(state_path, state)

            if status in ("REDIRECT", "RATE_LIMIT"):
                print("{0} STOP status={1} cooldown={2}".format(key, status, args.cooldown), flush=True)
                if args.cooldown > 0:
                    time.sleep(args.cooldown)
                break

            if status != "DRY_RUN" and args.sleep > 0:
                time.sleep(args.sleep)

    print("SUMMARY {0}".format(sorted(counts.items())), flush=True)
    save_state(state_path, state)


if __name__ == "__main__":
    main()
