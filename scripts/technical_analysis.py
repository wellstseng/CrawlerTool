#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import math
import os
from datetime import date, datetime, timedelta

import pandas as pd

from query_stock_data import DEFAULT_ROOT, connect, parse_date


MA_PERIODS = (5, 10, 20, 60, 120, 240)
PRESETS = (
    "breakout_20d",
    "breakdown_20d",
    "ma_bullish_alignment",
    "ma_bearish_alignment",
    "volume_surge",
    "rsi_oversold",
    "rsi_overbought",
    "macd_bullish_cross",
    "macd_bearish_cross",
    "near_52w_high",
    "near_52w_low",
)


def clean_number(value):
    if value is None:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float):
        return round(value, 4)
    return value


def to_json_value(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    value = clean_number(value)
    return value


def get_stock_meta(con, symbol):
    rows = con.execute(
        """
        select symbol, name, market, industry, listing_date
        from stock_list
        where symbol = ?
        order by listing_date nulls last
        """,
        [symbol],
    ).fetchall()
    result = []
    for row in rows:
        result.append({
            "symbol": row[0],
            "name": row[1],
            "market": row[2],
            "industry": row[3],
            "listing_date": to_json_value(row[4]),
        })
    return result


def load_price(con, symbol, market, start, end, lookback):
    filters = [
        "symbol = ?",
        "open is not null",
        "high is not null",
        "low is not null",
        "close is not null",
        "close > 0",
    ]
    params = [symbol]
    if market != "all":
        filters.append("market = ?")
        params.append(market)
    if start:
        filters.append("date >= ?")
        params.append(start)
    if end:
        filters.append("date <= ?")
        params.append(end)

    limit_sql = ""
    if lookback:
        limit_sql = "limit ?"
        params.append(lookback)

    sql = """
        select date, market, symbol, name, open, high, low, close, volume, amount, transactions
        from price
        where {filters}
        order by date desc
        {limit_sql}
    """.format(filters=" and ".join(filters), limit_sql=limit_sql)
    df = con.execute(sql, params).fetchdf()
    if df.empty:
        return df
    return df.sort_values("date").reset_index(drop=True)


def latest_price_date(con, end):
    if end:
        return end
    row = con.execute("select max(date) from price").fetchone()
    if not row or row[0] is None:
        raise SystemExit("price dataset is empty")
    return row[0]


def load_market_price(con, market, end, lookback, symbol_regex):
    end = latest_price_date(con, end)
    start_floor = end - timedelta(days=max(lookback * 3, 420))
    filters = [
        "p.date <= ?",
        "p.date >= ?",
        "p.open is not null",
        "p.high is not null",
        "p.low is not null",
        "p.close is not null",
        "p.close > 0",
        "regexp_matches(p.symbol, ?)",
        "p.symbol in (select distinct symbol from stock_list)",
    ]
    params = [end, start_floor, symbol_regex]
    if market != "all":
        filters.append("p.market = ?")
        params.append(market)

    sql = """
        select date, market, symbol, name, open, high, low, close, volume, amount, transactions
        from (
            select
                p.date, p.market, p.symbol, p.name, p.open, p.high, p.low, p.close,
                p.volume, p.amount, p.transactions,
                row_number() over (partition by p.market, p.symbol order by p.date desc) as rn
            from price p
            where {filters}
        )
        where rn <= ?
        order by market, symbol, date
    """.format(filters=" and ".join(filters))
    params.append(lookback)
    return con.execute(sql, params).fetchdf(), end


def filter_price_outliers(df):
    if len(df) < 3:
        return df, []
    prev_close = df["close"].shift(1)
    next_close = df["close"].shift(-1)
    low_spike = (df["close"] < prev_close * 0.3) & (df["close"] < next_close * 0.3)
    high_spike = (df["close"] > prev_close * 3) & (df["close"] > next_close * 3)
    mask = low_spike | high_spike
    if not mask.any():
        return df, []
    dates = [to_json_value(i) for i in df.loc[mask, "date"].tolist()]
    warning = "已排除疑似異常價 {0} 筆: {1}".format(len(dates), ",".join(dates[:10]))
    return df.loc[~mask].reset_index(drop=True), [warning]


def filter_price_outliers_for_group(df):
    cleaned, warnings = filter_price_outliers(df)
    return cleaned, len(warnings)


def add_indicators(df):
    out = df.copy()
    close = out["close"]
    high = out["high"]
    low = out["low"]
    volume = out["volume"]

    for period in MA_PERIODS:
        out["sma_{0}".format(period)] = close.rolling(period).mean()
    out["ema_12"] = close.ewm(span=12, adjust=False).mean()
    out["ema_26"] = close.ewm(span=26, adjust=False).mean()

    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    out["rsi_14"] = 100 - (100 / (1 + rs))
    out.loc[(avg_loss == 0) & (avg_gain > 0), "rsi_14"] = 100

    out["macd"] = out["ema_12"] - out["ema_26"]
    out["macd_signal"] = out["macd"].ewm(span=9, adjust=False).mean()
    out["macd_hist"] = out["macd"] - out["macd_signal"]

    lowest_9 = low.rolling(9).min()
    highest_9 = high.rolling(9).max()
    out["kd_k"] = ((close - lowest_9) / (highest_9 - lowest_9).replace(0, pd.NA)) * 100
    out["kd_d"] = out["kd_k"].rolling(3).mean()

    middle = close.rolling(20).mean()
    std = close.rolling(20).std()
    out["bb_middle"] = middle
    out["bb_upper"] = middle + std * 2
    out["bb_lower"] = middle - std * 2

    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    out["atr_14"] = tr.rolling(14).mean()

    out["volume_ma_5"] = volume.rolling(5).mean()
    out["volume_ma_20"] = volume.rolling(20).mean()
    out["high_20"] = high.rolling(20).max()
    out["low_20"] = low.rolling(20).min()
    out["high_60"] = high.rolling(60).max()
    out["low_60"] = low.rolling(60).min()
    out["high_252"] = high.rolling(252).max()
    out["low_252"] = low.rolling(252).min()
    out["prev_high_20"] = high.shift(1).rolling(20).max()
    out["prev_low_20"] = low.shift(1).rolling(20).min()
    return out


def value(row, key):
    return clean_number(row.get(key))


def classify_trend(latest):
    close = value(latest, "close")
    sma20 = value(latest, "sma_20")
    sma60 = value(latest, "sma_60")
    sma120 = value(latest, "sma_120")
    sma240 = value(latest, "sma_240")
    ema12 = value(latest, "ema_12")
    ema26 = value(latest, "ema_26")

    short = "insufficient"
    if close is not None and sma20 is not None and ema12 is not None and ema26 is not None:
        short = "bullish" if close >= sma20 and ema12 >= ema26 else "bearish" if close < sma20 else "neutral"

    mid = "insufficient"
    if close is not None and sma20 is not None and sma60 is not None:
        mid = "bullish" if close >= sma60 and sma20 >= sma60 else "bearish" if close < sma60 else "neutral"

    long = "insufficient"
    if close is not None and sma240 is not None:
        long = "above_ma240" if close >= sma240 else "below_ma240"

    alignment = "insufficient"
    if all(i is not None for i in (sma20, sma60, sma120, sma240)):
        if sma20 > sma60 > sma120 > sma240:
            alignment = "bullish_alignment"
        elif sma20 < sma60 < sma120 < sma240:
            alignment = "bearish_alignment"
        else:
            alignment = "mixed"

    return {
        "short": short,
        "mid": mid,
        "long": long,
        "ma_alignment": alignment,
    }


def build_signals(df):
    latest = df.iloc[-1]
    previous = df.iloc[-2] if len(df) >= 2 else None
    close = value(latest, "close")
    volume = value(latest, "volume")
    signals = []

    for period in (20, 60, 120, 240):
        ma = value(latest, "sma_{0}".format(period))
        if close is None or ma is None:
            continue
        signals.append("close_above_sma_{0}".format(period) if close >= ma else "close_below_sma_{0}".format(period))

    rsi = value(latest, "rsi_14")
    if rsi is not None:
        if rsi >= 70:
            signals.append("rsi_overbought")
        elif rsi <= 30:
            signals.append("rsi_oversold")
        else:
            signals.append("rsi_neutral")

    volume_ma20 = value(latest, "volume_ma_20")
    if volume is not None and volume_ma20:
        if volume >= volume_ma20 * 1.5:
            signals.append("volume_surge")
        elif volume <= volume_ma20 * 0.5:
            signals.append("volume_dry")

    prev_high20 = value(latest, "prev_high_20")
    prev_low20 = value(latest, "prev_low_20")
    if close is not None and prev_high20 is not None and close > prev_high20:
        signals.append("breakout_20d")
    if close is not None and prev_low20 is not None and close < prev_low20:
        signals.append("breakdown_20d")

    high252 = value(latest, "high_252")
    low252 = value(latest, "low_252")
    if close is not None and high252 is not None and close >= high252 * 0.95:
        signals.append("near_52w_high")
    if close is not None and low252 is not None and close <= low252 * 1.05:
        signals.append("near_52w_low")

    if previous is not None:
        macd = value(latest, "macd")
        macd_signal = value(latest, "macd_signal")
        prev_macd = value(previous, "macd")
        prev_signal = value(previous, "macd_signal")
        if all(i is not None for i in (macd, macd_signal, prev_macd, prev_signal)):
            if prev_macd <= prev_signal and macd > macd_signal:
                signals.append("macd_bullish_cross")
            elif prev_macd >= prev_signal and macd < macd_signal:
                signals.append("macd_bearish_cross")

    return signals


def volume_ratio(latest):
    volume = value(latest, "volume")
    volume_ma20 = value(latest, "volume_ma_20")
    if volume is None or not volume_ma20:
        return None
    return round(volume / volume_ma20, 4)


def pct_from_ma(latest, period):
    close = value(latest, "close")
    ma = value(latest, "sma_{0}".format(period))
    if close is None or not ma:
        return None
    return round((close / ma - 1) * 100, 4)


def summarize_row(df, outlier_count=0):
    latest = df.iloc[-1]
    trend = classify_trend(latest)
    signals = build_signals(df)
    close = value(latest, "close")
    prev_close = value(df.iloc[-2], "close") if len(df) >= 2 else None
    change_pct = None
    if close is not None and prev_close:
        change_pct = round((close / prev_close - 1) * 100, 4)
    return {
        "date": to_json_value(latest.get("date")),
        "market": to_json_value(latest.get("market")),
        "symbol": to_json_value(latest.get("symbol")),
        "name": to_json_value(latest.get("name")),
        "close": close,
        "change_pct": change_pct,
        "volume": value(latest, "volume"),
        "volume_ratio_20": volume_ratio(latest),
        "rsi_14": value(latest, "rsi_14"),
        "macd_hist": value(latest, "macd_hist"),
        "pct_from_sma20": pct_from_ma(latest, 20),
        "pct_from_sma60": pct_from_ma(latest, 60),
        "trend": trend,
        "signals": signals,
        "outlier_count": outlier_count,
    }


def build_levels(latest):
    return {
        "support_20d": value(latest, "low_20"),
        "resistance_20d": value(latest, "high_20"),
        "support_60d": value(latest, "low_60"),
        "resistance_60d": value(latest, "high_60"),
        "low_52w": value(latest, "low_252"),
        "high_52w": value(latest, "high_252"),
    }


def row_snapshot(row):
    keys = [
        "date", "market", "symbol", "name", "open", "high", "low", "close", "volume",
        "sma_5", "sma_10", "sma_20", "sma_60", "sma_120", "sma_240",
        "ema_12", "ema_26", "rsi_14", "macd", "macd_signal", "macd_hist",
        "kd_k", "kd_d", "bb_upper", "bb_middle", "bb_lower", "atr_14",
        "volume_ma_5", "volume_ma_20",
    ]
    return {key: to_json_value(row.get(key)) for key in keys}


def analyze(con, args):
    start = parse_date(args.start)
    end = parse_date(args.end)
    if args.adjusted:
        raise SystemExit("adjusted price is not available yet")

    meta = get_stock_meta(con, args.symbol)
    df = load_price(con, args.symbol, args.market, start, end, args.lookback)
    warnings = ["使用未復權價；跨除權息的長期均線與報酬率可能失真"]
    if not meta:
        warnings.append("symbol not found in stock_list")
    if df.empty:
        raise SystemExit("no price data for symbol: {0}".format(args.symbol))
    if args.filter_outliers:
        df, outlier_warnings = filter_price_outliers(df)
        warnings.extend(outlier_warnings)
        if df.empty:
            raise SystemExit("no price data after outlier filtering for symbol: {0}".format(args.symbol))
    if len(df) < 240:
        warnings.append("有效日線少於 240 根，長期均線不足")

    analyzed = add_indicators(df)
    latest = analyzed.iloc[-1]
    result = {
        "symbol": args.symbol,
        "meta": meta,
        "data": {
            "rows": len(analyzed),
            "start": to_json_value(analyzed.iloc[0]["date"]),
            "end": to_json_value(latest["date"]),
            "adjusted": False,
        },
        "latest": row_snapshot(latest),
        "trend": classify_trend(latest),
        "signals": build_signals(analyzed),
        "levels": build_levels(latest),
        "warnings": warnings,
    }
    if args.series_limit:
        result["series"] = [row_snapshot(row) for _, row in analyzed.tail(args.series_limit).iterrows()]
    return result


def analyze_market(con, args):
    end = parse_date(getattr(args, "date", None))
    df, actual_end = load_market_price(con, args.market, end, args.lookback, args.symbol_regex)
    if df.empty:
        raise SystemExit("no market price data")

    rows = []
    warnings = ["使用未復權價；跨除權息的長期均線與報酬率可能失真"]
    outlier_total = 0
    for _, group in df.groupby(["market", "symbol"], sort=False):
        group = group.reset_index(drop=True)
        if getattr(args, "filter_outliers", True):
            group, outlier_count = filter_price_outliers_for_group(group)
            outlier_total += outlier_count
        else:
            outlier_count = 0
        if group.empty:
            continue
        analyzed = add_indicators(group)
        latest_date = analyzed.iloc[-1]["date"]
        if not getattr(args, "include_stale", False):
            if hasattr(latest_date, "date"):
                latest_date = latest_date.date()
            if latest_date != actual_end:
                continue
        rows.append(summarize_row(analyzed, outlier_count))
    if outlier_total:
        warnings.append("已排除含疑似異常價的序列 {0} 檔".format(outlier_total))
    return rows, actual_end, warnings


def match_preset(row, preset):
    signals = set(row["signals"])
    trend = row["trend"]
    if preset in signals:
        return True
    if preset == "ma_bullish_alignment":
        return trend["ma_alignment"] == "bullish_alignment"
    if preset == "ma_bearish_alignment":
        return trend["ma_alignment"] == "bearish_alignment"
    return False


def screen(con, args):
    rows, actual_end, warnings = analyze_market(con, args)
    matched = [row for row in rows if match_preset(row, args.preset)]
    sort_key = args.sort
    reverse = not args.asc
    matched.sort(key=lambda row: row.get(sort_key) if row.get(sort_key) is not None else float("-inf"), reverse=reverse)
    if args.limit:
        matched = matched[:args.limit]
    return {
        "date": to_json_value(actual_end),
        "preset": args.preset,
        "market": args.market,
        "lookback": args.lookback,
        "count": len(matched),
        "rows": matched,
        "warnings": warnings,
    }


def ratio(count, total):
    if not total:
        return None
    return round(count / total * 100, 4)


def market_summary(con, args):
    rows, actual_end, warnings = analyze_market(con, args)
    total = len(rows)
    up = sum(1 for row in rows if row["change_pct"] is not None and row["change_pct"] > 0)
    down = sum(1 for row in rows if row["change_pct"] is not None and row["change_pct"] < 0)
    flat = sum(1 for row in rows if row["change_pct"] == 0)
    above20 = sum(1 for row in rows if "close_above_sma_20" in row["signals"])
    above60 = sum(1 for row in rows if "close_above_sma_60" in row["signals"])
    above240 = sum(1 for row in rows if "close_above_sma_240" in row["signals"])
    breakout = [row for row in rows if "breakout_20d" in row["signals"]]
    breakdown = [row for row in rows if "breakdown_20d" in row["signals"]]
    volume_surge = [row for row in rows if "volume_surge" in row["signals"]]
    bullish_alignment = [row for row in rows if row["trend"]["ma_alignment"] == "bullish_alignment"]
    bearish_alignment = [row for row in rows if row["trend"]["ma_alignment"] == "bearish_alignment"]

    def top(items, key, limit, reverse=True):
        return sorted(
            items,
            key=lambda row: row.get(key) if row.get(key) is not None else float("-inf"),
            reverse=reverse,
        )[:limit]

    return {
        "date": to_json_value(actual_end),
        "market": args.market,
        "lookback": args.lookback,
        "universe": {
            "symbols": total,
            "up": up,
            "down": down,
            "flat": flat,
            "up_ratio": ratio(up, total),
            "down_ratio": ratio(down, total),
        },
        "breadth": {
            "above_sma20": above20,
            "above_sma20_ratio": ratio(above20, total),
            "above_sma60": above60,
            "above_sma60_ratio": ratio(above60, total),
            "above_sma240": above240,
            "above_sma240_ratio": ratio(above240, total),
            "breakout_20d": len(breakout),
            "breakdown_20d": len(breakdown),
            "volume_surge": len(volume_surge),
            "ma_bullish_alignment": len(bullish_alignment),
            "ma_bearish_alignment": len(bearish_alignment),
        },
        "top": {
            "gainers": top(rows, "change_pct", args.limit),
            "losers": top(rows, "change_pct", args.limit, False),
            "volume_surge": top(volume_surge, "volume_ratio_20", args.limit),
            "breakout_20d": top(breakout, "volume_ratio_20", args.limit),
            "breakdown_20d": top(breakdown, "volume_ratio_20", args.limit),
        },
        "warnings": warnings,
    }


def emit_json(result):
    print(json.dumps(result, ensure_ascii=False, indent=2))


def emit_table(result):
    latest = result["latest"]
    rows = [
        ("symbol", result["symbol"]),
        ("date", latest["date"]),
        ("name", latest["name"]),
        ("close", latest["close"]),
        ("volume", latest["volume"]),
        ("sma20", latest["sma_20"]),
        ("sma60", latest["sma_60"]),
        ("sma240", latest["sma_240"]),
        ("rsi14", latest["rsi_14"]),
        ("macd", latest["macd"]),
        ("macd_signal", latest["macd_signal"]),
        ("trend_short", result["trend"]["short"]),
        ("trend_mid", result["trend"]["mid"]),
        ("trend_long", result["trend"]["long"]),
        ("signals", ",".join(result["signals"])),
    ]
    width = max(len(key) for key, _ in rows)
    for key, val in rows:
        print("{0} : {1}".format(key.ljust(width), val))
    if result["warnings"]:
        print("warnings : {0}".format("; ".join(result["warnings"])))


def emit_rows_table(rows):
    columns = ("date", "market", "symbol", "name", "close", "change_pct", "volume_ratio_20", "rsi_14", "signals")
    if not rows:
        print("(no rows)")
        return
    printable = []
    for row in rows:
        item = {key: row.get(key) for key in columns}
        item["signals"] = ",".join(row.get("signals", []))
        printable.append(item)
    widths = {key: len(key) for key in columns}
    for row in printable:
        for key in columns:
            widths[key] = max(widths[key], len(str(row.get(key, ""))))
    print(" | ".join(key.ljust(widths[key]) for key in columns))
    print("-+-".join("-" * widths[key] for key in columns))
    for row in printable:
        print(" | ".join(str(row.get(key, "")).ljust(widths[key]) for key in columns))


def emit_summary_table(result):
    universe = result["universe"]
    breadth = result["breadth"]
    rows = [
        ("date", result["date"]),
        ("market", result["market"]),
        ("symbols", universe["symbols"]),
        ("up/down/flat", "{0}/{1}/{2}".format(universe["up"], universe["down"], universe["flat"])),
        ("up_ratio", universe["up_ratio"]),
        ("above_sma20", "{0} ({1}%)".format(breadth["above_sma20"], breadth["above_sma20_ratio"])),
        ("above_sma60", "{0} ({1}%)".format(breadth["above_sma60"], breadth["above_sma60_ratio"])),
        ("above_sma240", "{0} ({1}%)".format(breadth["above_sma240"], breadth["above_sma240_ratio"])),
        ("breakout_20d", breadth["breakout_20d"]),
        ("breakdown_20d", breadth["breakdown_20d"]),
        ("volume_surge", breadth["volume_surge"]),
        ("ma_bullish_alignment", breadth["ma_bullish_alignment"]),
        ("ma_bearish_alignment", breadth["ma_bearish_alignment"]),
    ]
    width = max(len(key) for key, _ in rows)
    for key, val in rows:
        print("{0} : {1}".format(key.ljust(width), val))
    print("")
    print("top volume_surge")
    emit_rows_table(result["top"]["volume_surge"])
    if result["warnings"]:
        print("warnings : {0}".format("; ".join(result["warnings"])))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=os.environ.get("STOCK_RESOURCE_PATH", DEFAULT_ROOT))
    sub = parser.add_subparsers(dest="command", required=True)

    analyze_parser = sub.add_parser("analyze")
    analyze_parser.add_argument("--symbol", required=True)
    analyze_parser.add_argument("--market", default="all", choices=("all", "twse", "tpex"))
    analyze_parser.add_argument("--start")
    analyze_parser.add_argument("--end")
    analyze_parser.add_argument("--lookback", type=int, default=300)
    analyze_parser.add_argument("--adjusted", action="store_true")
    analyze_parser.add_argument("--filter-outliers", action=argparse.BooleanOptionalAction, default=True)
    analyze_parser.add_argument("--series-limit", type=int, default=0)
    analyze_parser.add_argument("--format", choices=("json", "table"), default="json")

    screen_parser = sub.add_parser("screen")
    screen_parser.add_argument("--preset", required=True, choices=PRESETS)
    screen_parser.add_argument("--market", default="all", choices=("all", "twse", "tpex"))
    screen_parser.add_argument("--date")
    screen_parser.add_argument("--lookback", type=int, default=300)
    screen_parser.add_argument("--symbol-regex", default="^[0-9]{4}$")
    screen_parser.add_argument("--limit", type=int, default=50)
    screen_parser.add_argument("--sort", default="volume_ratio_20", choices=("volume_ratio_20", "change_pct", "rsi_14", "close"))
    screen_parser.add_argument("--asc", action="store_true")
    screen_parser.add_argument("--filter-outliers", action=argparse.BooleanOptionalAction, default=True)
    screen_parser.add_argument("--include-stale", action="store_true")
    screen_parser.add_argument("--format", choices=("json", "table"), default="json")

    summary_parser = sub.add_parser("market-summary")
    summary_parser.add_argument("--market", default="all", choices=("all", "twse", "tpex"))
    summary_parser.add_argument("--date")
    summary_parser.add_argument("--lookback", type=int, default=300)
    summary_parser.add_argument("--symbol-regex", default="^[0-9]{4}$")
    summary_parser.add_argument("--limit", type=int, default=10)
    summary_parser.add_argument("--filter-outliers", action=argparse.BooleanOptionalAction, default=True)
    summary_parser.add_argument("--include-stale", action="store_true")
    summary_parser.add_argument("--format", choices=("json", "table"), default="json")

    args = parser.parse_args()
    con = connect(args.root)
    try:
        if args.command == "analyze":
            result = analyze(con, args)
            if args.format == "table":
                emit_table(result)
            else:
                emit_json(result)
        elif args.command == "screen":
            result = screen(con, args)
            if args.format == "table":
                emit_rows_table(result["rows"])
                if result["warnings"]:
                    print("warnings : {0}".format("; ".join(result["warnings"])))
            else:
                emit_json(result)
        elif args.command == "market-summary":
            result = market_summary(con, args)
            if args.format == "table":
                emit_summary_table(result)
            else:
                emit_json(result)
    finally:
        con.close()


if __name__ == "__main__":
    main()
