#!/usr/bin/env python3
"""Small CLI to list markets from the SQLite demo DB.

Usage examples:
  PYTHONPATH=src python scripts/list_markets.py --db pm_arb_demo.db
  PYTHONPATH=src python scripts/list_markets.py --db pm_arb_demo.db --source polymarket --show-contracts
"""
from __future__ import annotations

import argparse
from typing import Optional


def main() -> None:
    parser = argparse.ArgumentParser(description="List markets from pm_arb SQLite DB")
    parser.add_argument("--db", default="pm_arb_demo.db", help="SQLite DB path or SQLAlchemy URL")
    parser.add_argument("--source", help="Filter by source (kalshi|polymarket|predictit)")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--show-contracts", action="store_true", help="Also print contract rows")
    args = parser.parse_args()

    # import local package (requires PYTHONPATH=src when running from repo root)
    try:
        from pm_arb.sql_storage import init_db, MarketORM
    except Exception as e:
        print("Failed to import package. Run with `PYTHONPATH=src` from repo root.")
        raise

    db_url = args.db
    # if a plain filename provided, convert to sqlite URL
    if not db_url.startswith("sqlite:"):
        db_url = f"sqlite:///{db_url}"

    engine, SessionLocal = init_db(db_url)
    session = SessionLocal()

    q = session.query(MarketORM)
    if args.source:
        q = q.filter(MarketORM.source == args.source)
    q = q.order_by(MarketORM.id).limit(args.limit)

    rows = q.all()
    if not rows:
        print("No markets found")
        return

    for m in rows:
        print(f"{m.id}\t{m.source}\t{m.market_id}\t{m.name}")
        if args.show_contracts:
            for c in m.contracts:
                print(f"    - {c.contract_id}\t{c.name}\tbid={c.price_bid}\task={c.price_ask}\tlast={c.last_price}")

    session.close()


if __name__ == "__main__":
    main()
