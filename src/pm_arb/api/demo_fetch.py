from __future__ import annotations

import argparse

from . import (
    KalshiClient,
    PolymarketClient,
    PredictItClient,
)
from .. import sql_storage


def main(no_save: bool = False) -> None:
    # initialize a small local SQLite DB for the demo
    engine, SessionLocal = sql_storage.init_db("sqlite:///pm_arb_demo.db")
    session = SessionLocal()

    print("=== Kalshi ===")
    k = KalshiClient()
    k_markets = k.list_markets(limit=5)
    saved = False
    for raw in k_markets:
        ticker = raw.get("ticker")
        ob = k.get_orderbook(ticker)
        uni = k.normalize_market(raw, ob)
        c = uni.contracts[0]
        print(f"- {uni.market_id}: {uni.name}")
        print(f"    YES bid={c.price_bid}, ask={c.price_ask}")
        if not saved and not no_save:
            sql_storage.save_market(session, uni)
            saved = True

    print("\n=== Polymarket ===")
    p = PolymarketClient()
    p_markets = p.list_markets(limit=5)
    saved = False
    for raw in p_markets[:3]:
        uni = p.normalize_market(raw)
        prices = [c.last_price for c in uni.contracts]
        print(f"- {uni.market_id}: {uni.name}")
        print(f"    prices={prices}")
        if not saved and not no_save:
            sql_storage.save_market(session, uni)
            saved = True

    print("\n=== PredictIt ===")
    pi = PredictItClient()
    pi_markets = pi.list_markets()
    saved = False
    for raw in pi_markets[:3]:
        uni = pi.normalize_market(raw)
        prices = [c.last_price for c in uni.contracts]
        print(f"- {uni.market_id}: {uni.name}")
        print(f"    prices={prices}")
        if not saved and not no_save:
            sql_storage.save_market(session, uni)
            saved = True

    # show how to load back a market from the DB (example)
    example = session.query(sql_storage.MarketORM).first()
    if example:
        loaded = sql_storage.load_market(session, example.source, example.market_id)
        if loaded:
            print(
                f"\nLoaded from DB: {loaded.market_id} ({len(loaded.contracts)} contracts)"
            )

    session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--no-save", action="store_true", help="Don't write to the demo DB; dry-run"
    )
    args = parser.parse_args()

    main(no_save=args.no_save)
