from __future__ import annotations

from . import (
    KalshiClient,
    PolymarketClient,
    PredictItClient,
)


def main() -> None:
    print("=== Kalshi ===")
    k = KalshiClient()
    k_markets = k.list_markets(limit=5)
    for raw in k_markets:
        ticker = raw.get("ticker")
        ob = k.get_orderbook(ticker)
        uni = k.normalize_market(raw, ob)
        c = uni.contracts[0]
        print(f"- {uni.market_id}: {uni.name}")
        print(f"    YES bid={c.price_bid}, ask={c.price_ask}")

    print("\n=== Polymarket ===")
    p = PolymarketClient()
    p_markets = p.list_markets(limit=5)
    for raw in p_markets[:3]:
        uni = p.normalize_market(raw)
        prices = [c.last_price for c in uni.contracts]
        print(f"- {uni.market_id}: {uni.name}")
        print(f"    prices={prices}")

    print("\n=== PredictIt ===")
    pi = PredictItClient()
    pi_markets = pi.list_markets()
    for raw in pi_markets[:3]:
        uni = pi.normalize_market(raw)
        prices = [c.last_price for c in uni.contracts]
        print(f"- {uni.market_id}: {uni.name}")
        print(f"    prices={prices}")


if __name__ == "__main__":
    main()
