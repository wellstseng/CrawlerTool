#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import csv
import json
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path

import duckdb


DEFAULT_ROOT = "/Users/wellstseng/project/StockResource"
DATASETS = {
    "price": "parquet/price/**/*.parquet",
    "margin": "parquet/margin/**/*.parquet",
    "day_trading": "parquet/day_trading/**/*.parquet",
    "stock_list": "parquet/stock_list/*.parquet",
}
DATE_DATASETS = {"price", "margin", "day_trading"}
IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def sql_literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def parse_date(value):
    if not value:
        return None
    value = value.strip()
    for fmt in ("%Y%m%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    raise SystemExit("bad date: {0}".format(value))


def normalize_columns(value):
    if not value or value == "*":
        return "*"
    columns = [i.strip() for i in value.split(",") if i.strip()]
    for column in columns:
        if not IDENT_RE.match(column):
            raise SystemExit("bad column: {0}".format(column))
    return ", ".join(columns)


def normalize_dataset(value):
    if value not in DATASETS:
        raise SystemExit("bad dataset: {0}".format(value))
    return value


def connect(root):
    root = Path(root)
    con = duckdb.connect(":memory:")
    for name, rel_path in DATASETS.items():
        path = root / rel_path
        con.execute("create view {0} as select * from read_parquet({1})".format(name, sql_literal(path)))
    return con


def rows_to_dicts(cursor):
    columns = [item[0] for item in cursor.description]
    rows = []
    for row in cursor.fetchall():
        record = {}
        for column, value in zip(columns, row):
            if isinstance(value, (date, datetime)):
                value = value.isoformat()
            record[column] = value
        rows.append(record)
    return columns, rows


def emit(columns, rows, output_format):
    if output_format == "json":
        print(json.dumps({"columns": columns, "rows": rows}, ensure_ascii=False, indent=2))
        return
    if output_format == "jsonl":
        for row in rows:
            print(json.dumps(row, ensure_ascii=False))
        return
    if output_format == "csv":
        writer = csv.DictWriter(sys.stdout, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        return
    if output_format == "table":
        if not rows:
            print("(no rows)")
            return
        widths = {column: len(column) for column in columns}
        for row in rows:
            for column in columns:
                widths[column] = max(widths[column], len(str(row.get(column, ""))))
        print(" | ".join(column.ljust(widths[column]) for column in columns))
        print("-+-".join("-" * widths[column] for column in columns))
        for row in rows:
            print(" | ".join(str(row.get(column, "")).ljust(widths[column]) for column in columns))


def build_filters(args, dataset, prefix=""):
    filters = []
    params = []
    name = (lambda column: "{0}.{1}".format(prefix, column)) if prefix else (lambda column: column)

    if getattr(args, "symbol", None):
        filters.append(name("symbol") + " = ?")
        params.append(args.symbol)
    if getattr(args, "market", None) and args.market != "all":
        filters.append(name("market") + " = ?")
        params.append(args.market)
    if dataset in DATE_DATASETS:
        start = parse_date(getattr(args, "start", None))
        end = parse_date(getattr(args, "end", None))
        if start:
            filters.append(name("date") + " >= ?")
            params.append(start)
        if end:
            filters.append(name("date") + " <= ?")
            params.append(end)
    if getattr(args, "industry", None) and dataset == "stock_list":
        filters.append(name("industry") + " = ?")
        params.append(args.industry)
    if getattr(args, "name_like", None):
        filters.append(name("name") + " like ?")
        params.append("%" + args.name_like + "%")
    if getattr(args, "where_sql", None):
        filters.append("(" + args.where_sql + ")")
    return filters, params


def command_schema(con, args):
    datasets = DATASETS if args.dataset == "all" else {normalize_dataset(args.dataset): DATASETS[args.dataset]}
    result = []
    for dataset in datasets:
        rows = con.execute("describe {0}".format(dataset)).fetchall()
        result.append({
            "dataset": dataset,
            "columns": [{"name": row[0], "type": row[1]} for row in rows],
        })
    print(json.dumps(result, ensure_ascii=False, indent=2))


def command_query(con, args):
    dataset = normalize_dataset(args.dataset)
    columns = normalize_columns(args.columns)
    filters, params = build_filters(args, dataset)
    sql = ["select {0} from {1}".format(columns, dataset)]
    if filters:
        sql.append("where " + " and ".join(filters))
    if dataset in DATE_DATASETS:
        direction = "asc" if args.asc else "desc"
        sql.append("order by date {0}, symbol asc".format(direction))
    elif args.order_by:
        if not IDENT_RE.match(args.order_by):
            raise SystemExit("bad order column: {0}".format(args.order_by))
        sql.append("order by {0}".format(args.order_by))
    if args.limit:
        sql.append("limit ?")
        params.append(args.limit)

    cursor = con.execute("\n".join(sql), params)
    emit(*rows_to_dicts(cursor), args.format)


def command_joined(con, args):
    filters, params = build_filters(args, "price", "p")
    fields = [
        "p.date", "p.market", "p.symbol", "p.name", "p.open", "p.high", "p.low", "p.close",
        "p.volume", "p.amount", "p.transactions",
        "m.margin_buy", "m.margin_sell", "m.margin_balance", "m.short_sell", "m.short_balance", "m.offset",
        "d.day_trade_volume", "d.day_trade_buy_amount", "d.day_trade_sell_amount",
    ]
    sql = [
        "select {0}".format(", ".join(fields)),
        "from price p",
        "left join margin m on p.date = m.date and p.market = m.market and p.symbol = m.symbol",
        "left join day_trading d on p.date = d.date and p.market = d.market and p.symbol = d.symbol",
    ]
    if filters:
        sql.append("where " + " and ".join(filters))
    direction = "asc" if args.asc else "desc"
    sql.append("order by p.date {0}, p.symbol asc".format(direction))
    if args.limit:
        sql.append("limit ?")
        params.append(args.limit)

    cursor = con.execute("\n".join(sql), params)
    emit(*rows_to_dicts(cursor), args.format)


def command_sql(con, args):
    if args.file:
        query = Path(args.file).read_text(encoding="utf8")
    else:
        query = args.query
    if not query:
        raise SystemExit("--query or --file is required")
    cursor = con.execute(query)
    emit(*rows_to_dicts(cursor), args.format)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=os.environ.get("STOCK_RESOURCE_PATH", DEFAULT_ROOT))
    sub = parser.add_subparsers(dest="command", required=True)

    schema = sub.add_parser("schema")
    schema.add_argument("--dataset", default="all")

    query = sub.add_parser("query")
    query.add_argument("--dataset", required=True)
    query.add_argument("--symbol")
    query.add_argument("--market", default="all")
    query.add_argument("--start")
    query.add_argument("--end")
    query.add_argument("--industry")
    query.add_argument("--name-like")
    query.add_argument("--where-sql")
    query.add_argument("--columns", default="*")
    query.add_argument("--order-by")
    query.add_argument("--asc", action="store_true")
    query.add_argument("--limit", type=int, default=100)
    query.add_argument("--format", choices=("json", "jsonl", "csv", "table"), default="json")

    joined = sub.add_parser("joined")
    joined.add_argument("--symbol")
    joined.add_argument("--market", default="all")
    joined.add_argument("--start")
    joined.add_argument("--end")
    joined.add_argument("--name-like")
    joined.add_argument("--where-sql")
    joined.add_argument("--asc", action="store_true")
    joined.add_argument("--limit", type=int, default=100)
    joined.add_argument("--format", choices=("json", "jsonl", "csv", "table"), default="json")

    sql = sub.add_parser("sql")
    sql.add_argument("--query")
    sql.add_argument("--file")
    sql.add_argument("--format", choices=("json", "jsonl", "csv", "table"), default="json")

    args = parser.parse_args()
    con = connect(args.root)
    try:
        if args.command == "schema":
            command_schema(con, args)
        elif args.command == "query":
            command_query(con, args)
        elif args.command == "joined":
            command_joined(con, args)
        elif args.command == "sql":
            command_sql(con, args)
    finally:
        con.close()


if __name__ == "__main__":
    main()
