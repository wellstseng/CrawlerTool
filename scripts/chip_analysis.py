#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import os
from datetime import date, datetime
from pathlib import Path

from query_stock_data import DEFAULT_ROOT, connect, parse_date


DEFAULT_LIMIT = 20
DAY_TRADE_RISK_RATIO = 30.0


def sql_date(value):
    return "date '{0}'".format(value.isoformat())


def json_value(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if hasattr(value, "item"):
        value = value.item()
    return value


def rows_to_dicts(cursor):
    columns = [item[0] for item in cursor.description]
    result = []
    for row in cursor.fetchall():
        result.append({column: json_value(value) for column, value in zip(columns, row)})
    return result


def one_row(con, query):
    cursor = con.execute(query)
    rows = rows_to_dicts(cursor)
    return rows[0] if rows else {}


def many_rows(con, query, limit=None):
    if limit is not None:
        query = query + "\nlimit {0}".format(int(limit))
    return rows_to_dicts(con.execute(query))


def parse_analysis_date(value, con):
    if value == "latest":
        row = con.execute("select max(date) from price").fetchone()
        if not row or row[0] is None:
            raise SystemExit("price dataset is empty")
        return row[0]
    return parse_date(value)


def create_base_view(con, target_date):
    target = sql_date(target_date)
    con.execute(
        """
        create or replace temp view chip_base as
        with stock_meta as (
            select
                symbol,
                any_value(name) as list_name,
                any_value(industry) as industry,
                any_value(market) as list_market
            from stock_list
            group by symbol
        ),
        price_enriched as (
            select *
            from (
                select
                    p.date,
                    p.market,
                    p.symbol,
                    p.name,
                    p.open,
                    p.high,
                    p.low,
                    p.close,
                    p.volume,
                    p.amount,
                    p.transactions,
                    lag(p.close) over (partition by p.market, p.symbol order by p.date) as prev_close,
                    avg(p.volume) over (
                        partition by p.market, p.symbol
                        order by p.date
                        rows between 20 preceding and 1 preceding
                    ) as volume_ma20
                from price p
                where p.date <= {target}
                  and p.date >= {target} - interval 90 day
                  and p.open is not null
                  and p.high is not null
                  and p.low is not null
                  and p.close is not null
                  and p.close > 0
                  and regexp_matches(p.symbol, '^[0-9]{{4}}$')
            )
            where date = {target}
        )
        select
            p.date,
            p.market,
            p.symbol,
            coalesce(sm.list_name, p.name) as name,
            sm.industry,
            p.open,
            p.high,
            p.low,
            p.close,
            p.prev_close,
            case
                when p.prev_close is not null and p.prev_close != 0
                then round((p.close / p.prev_close - 1) * 100, 4)
                else null
            end as price_change_pct,
            p.volume,
            case
                when p.volume_ma20 is not null and p.volume_ma20 != 0
                then round(p.volume / p.volume_ma20, 4)
                else null
            end as volume_ratio_20,
            l.foreign_net,
            l.investment_trust_net,
            l.dealer_net,
            l.total_net,
            m.margin_buy,
            m.margin_sell,
            m.margin_prev_balance,
            m.margin_balance,
            m.margin_balance - m.margin_prev_balance as margin_balance_change,
            d.day_trade_volume,
            d.day_trade_buy_amount,
            d.day_trade_sell_amount,
            case
                when p.volume is not null and p.volume != 0 and d.day_trade_volume is not null
                then round(d.day_trade_volume * 100.0 / p.volume, 4)
                else null
            end as day_trade_ratio
        from price_enriched p
        left join stock_meta sm
            on p.symbol = sm.symbol
        left join legal_person l
            on p.date = l.date
           and p.market = l.market
           and p.symbol = l.symbol
        left join margin m
            on p.date = m.date
           and p.market = m.market
           and p.symbol = m.symbol
        left join day_trading d
            on p.date = d.date
           and p.market = d.market
           and p.symbol = d.symbol
        """.format(target=target)
    )


def source_status(con, target_date):
    target = sql_date(target_date)
    result = {}
    for name in ("price", "legal_person", "margin", "day_trading"):
        result[name] = one_row(con, """
            select
                count(*) as rows,
                min(date) as min_date,
                max(date) as max_date,
                sum(case when date = {target} then 1 else 0 end) as target_rows
            from {name}
        """.format(name=name, target=target))
    return result


def totals(con):
    return one_row(con, """
        select
            coalesce(sum(foreign_net), 0) as foreign_net,
            coalesce(sum(investment_trust_net), 0) as investment_trust_net,
            coalesce(sum(dealer_net), 0) as dealer_net,
            coalesce(sum(total_net), 0) as total_net,
            count(*) filter (where total_net is not null) as symbols_with_legal_person
        from chip_base
    """)


def ranking(con, field, direction, limit):
    order = "desc" if direction == "buy" else "asc"
    return many_rows(con, """
        select
            date, market, symbol, name, industry, close, price_change_pct,
            volume_ratio_20, {field} as net
        from chip_base
        where {field} is not null
        order by {field} {order}
    """.format(field=field, order=order), limit)


def legal_rankings(con, limit):
    return {
        "foreign": {
            "buy": ranking(con, "foreign_net", "buy", limit),
            "sell": ranking(con, "foreign_net", "sell", limit),
        },
        "investment_trust": {
            "buy": ranking(con, "investment_trust_net", "buy", limit),
            "sell": ranking(con, "investment_trust_net", "sell", limit),
        },
        "dealer": {
            "buy": ranking(con, "dealer_net", "buy", limit),
            "sell": ranking(con, "dealer_net", "sell", limit),
        },
    }


def industry_flow(con, limit):
    return many_rows(con, """
        select
            coalesce(industry, '') as industry,
            count(*) as symbols,
            coalesce(sum(foreign_net), 0) as foreign_net,
            coalesce(sum(investment_trust_net), 0) as investment_trust_net,
            coalesce(sum(dealer_net), 0) as dealer_net,
            coalesce(sum(total_net), 0) as total_net
        from chip_base
        where total_net is not null
        group by coalesce(industry, '')
        order by abs(coalesce(sum(total_net), 0)) desc
    """, limit)


def margin_rankings(con, limit):
    columns = """
        date, market, symbol, name, industry, close, price_change_pct,
        margin_prev_balance, margin_balance, margin_balance_change
    """
    return {
        "increase": many_rows(con, """
            select {columns}
            from chip_base
            where margin_balance_change is not null
            order by margin_balance_change desc
        """.format(columns=columns), limit),
        "decrease": many_rows(con, """
            select {columns}
            from chip_base
            where margin_balance_change is not null
            order by margin_balance_change asc
        """.format(columns=columns), limit),
    }


def day_trading_heat(con, limit):
    return many_rows(con, """
        select
            date, market, symbol, name, industry, close, price_change_pct,
            volume, day_trade_volume, day_trade_ratio,
            day_trade_buy_amount, day_trade_sell_amount
        from chip_base
        where day_trade_ratio is not null
        order by day_trade_ratio desc, day_trade_volume desc
    """, limit)


def divergence_signals(con, limit, day_trade_risk_ratio):
    base = "date, market, symbol, name, industry, close, price_change_pct, volume_ratio_20"
    return {
        "price_up_foreign_sell": many_rows(con, """
            select {base}, foreign_net
            from chip_base
            where price_change_pct > 0 and foreign_net < 0
            order by abs(foreign_net) desc
        """.format(base=base), limit),
        "price_down_investment_trust_buy": many_rows(con, """
            select {base}, investment_trust_net
            from chip_base
            where price_change_pct < 0 and investment_trust_net > 0
            order by investment_trust_net desc
        """.format(base=base), limit),
        "margin_increase_price_weak": many_rows(con, """
            select {base}, margin_balance_change, margin_balance, margin_prev_balance
            from chip_base
            where price_change_pct < 0 and margin_balance_change > 0
            order by margin_balance_change desc
        """.format(base=base), limit),
        "high_day_trading_ratio_risk": many_rows(con, """
            select {base}, day_trade_volume, day_trade_ratio
            from chip_base
            where day_trade_ratio >= {ratio}
            order by day_trade_ratio desc, day_trade_volume desc
        """.format(base=base, ratio=float(day_trade_risk_ratio)), limit),
    }


def build_warnings(status):
    warnings = []
    for name, info in status.items():
        if not info.get("target_rows"):
            warnings.append("{0} has no rows for target date".format(name))
    return warnings


def build_analysis(con, root, target_date, limit, day_trade_risk_ratio):
    create_base_view(con, target_date)
    status = source_status(con, target_date)
    return {
        "date": target_date.isoformat(),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "root": str(root),
        "source_status": status,
        "totals": totals(con),
        "rankings": legal_rankings(con, limit),
        "industry_flow": industry_flow(con, limit),
        "margin": margin_rankings(con, limit),
        "day_trading_heat": day_trading_heat(con, limit),
        "divergence_signals": divergence_signals(con, limit, day_trade_risk_ratio),
        "warnings": build_warnings(status),
    }


def write_output(root, target_date, analysis, output):
    if output:
        path = Path(output)
    else:
        path = Path(root) / "analysis" / "{0}_chip_analysis.json".format(target_date.isoformat())
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=os.environ.get("STOCK_RESOURCE_PATH", DEFAULT_ROOT))
    parser.add_argument("--date", required=True, help="YYYY-MM-DD, YYYYMMDD, or latest")
    parser.add_argument("--output")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--day-trade-risk-ratio", type=float, default=DAY_TRADE_RISK_RATIO)
    args = parser.parse_args()

    root = Path(args.root)
    con = connect(root)
    try:
        target_date = parse_analysis_date(args.date, con)
        analysis = build_analysis(con, root, target_date, args.limit, args.day_trade_risk_ratio)
        path = write_output(root, target_date, analysis, args.output)
        print(path)
    finally:
        con.close()


if __name__ == "__main__":
    main()
