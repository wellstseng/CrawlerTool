#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
from pathlib import Path

import duckdb


DEFAULT_ROOT = "/Users/wellstseng/project/StockResource"
DATASETS = {
    "price": "parquet/price/**/*.parquet",
    "margin": "parquet/margin/**/*.parquet",
    "day_trading": "parquet/day_trading/**/*.parquet",
    "legal_person": "parquet/legal_person/**/*.parquet",
    "stock_list": "parquet/stock_list/*.parquet",
}


def sql_literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=os.environ.get("STOCK_RESOURCE_PATH", DEFAULT_ROOT))
    parser.add_argument("--database", help="default: <root>/stock.duckdb")
    args = parser.parse_args()

    root = Path(args.root)
    db_path = Path(args.database) if args.database else root / "stock.duckdb"
    con = duckdb.connect(str(db_path))
    try:
        for name, rel_path in DATASETS.items():
            path = root / rel_path
            con.execute("create or replace view {0} as select * from read_parquet({1})".format(name, sql_literal(path)))

        for name in DATASETS:
            count = con.execute("select count(*) from {0}".format(name)).fetchone()[0]
            print("{0} rows={1}".format(name, count))
    finally:
        con.close()


if __name__ == "__main__":
    main()
