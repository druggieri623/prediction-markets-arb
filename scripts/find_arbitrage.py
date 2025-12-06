#!/usr/bin/env python
"""
Market matching for arbitrage detection.

This script demonstrates how to use the matcher to find potential
price discrepancies (arbitrage opportunities) across platforms.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pm_arb.sql_storage import init_db, MarketORM, load_market
from pm_arb.matcher import MarketMatcher
import argparse


def find_arbitrage_opportunities(db_path: str, min_spread: float = 0.05):
    """
    Find potential arbitrage opportunities across matched markets.

    An arbitrage opportunity exists when:
    1. Two markets are matched across platforms
    2. For the same contract (e.g., YES), ask price on one platform < bid price on another

    Args:
        db_path: Path to SQLite database
        min_spread: Minimum bid-ask spread to consider (default 5%)
    """
    # Initialize database
    engine, SessionLocal = init_db(f"sqlite:///{db_path}")
    session = SessionLocal()

    try:
        # Load all markets
        market_orms = session.query(MarketORM).all()
        if not market_orms:
            print("No markets found in database")
            return

        markets = []
        for market_orm in market_orms:
            market = load_market(session, market_orm.source, market_orm.market_id)
            if market:
                markets.append(market)

        # Find matches
        matcher = MarketMatcher(min_score_threshold=0.5)
        matches = matcher.find_matches(markets, cross_source_only=True)

        print("\n" + "=" * 80)
        print("ARBITRAGE OPPORTUNITY SCANNER")
        print("=" * 80)

        opportunities = []

        for match in matches:
            # Only consider high/medium confidence matches
            if match.confidence not in ["high", "medium"]:
                continue

            market_a = match.market_a
            market_b = match.market_b

            # Skip if no contracts to match
            if not market_a.contracts or not market_b.contracts:
                continue

            # Check each matched contract pair for price discrepancies
            for contract_a, contract_b in match.matching_contracts:
                # Extract prices
                bid_a = contract_a.price_bid
                ask_a = contract_a.price_ask
                bid_b = contract_b.price_bid
                ask_b = contract_b.price_ask

                # Skip if missing prices
                if not all([bid_a, ask_a, bid_b, ask_b]):
                    continue

                # Check for arbitrage: buy low on B, sell high on A
                if ask_b < bid_a:
                    spread = bid_a - ask_b
                    spread_pct = (spread / ask_b) * 100

                    if spread_pct >= min_spread:
                        opportunities.append(
                            {
                                "market_a": market_a.name[:60],
                                "market_a_source": market_a.source,
                                "market_b_source": market_b.source,
                                "contract": contract_a.name,
                                "buy_at": ask_b,
                                "sell_at": bid_a,
                                "spread": spread,
                                "spread_pct": spread_pct,
                                "profit_per_share": spread,
                                "match_score": match.match_score,
                                "confidence": match.confidence,
                            }
                        )

                # Check reverse direction: buy low on A, sell high on B
                if ask_a < bid_b:
                    spread = bid_b - ask_a
                    spread_pct = (spread / ask_a) * 100

                    if spread_pct >= min_spread:
                        opportunities.append(
                            {
                                "market_a": market_a.name[:60],
                                "market_a_source": market_b.source,
                                "market_b_source": market_a.source,
                                "contract": contract_a.name,
                                "buy_at": ask_a,
                                "sell_at": bid_b,
                                "spread": spread,
                                "spread_pct": spread_pct,
                                "profit_per_share": spread,
                                "match_score": match.match_score,
                                "confidence": match.confidence,
                            }
                        )

        # Display results
        if not opportunities:
            print(f"\nNo arbitrage opportunities found above {min_spread}% threshold\n")
            return

        # Sort by spread (highest first)
        opportunities.sort(key=lambda x: x["spread_pct"], reverse=True)

        print(
            f"\nFound {len(opportunities)} arbitrage opportunity(ies) above {min_spread}% threshold\n"
        )

        for i, opp in enumerate(opportunities, 1):
            print(f"\n{i}. ARBITRAGE OPPORTUNITY")
            print("-" * 80)
            print(f"Market: {opp['market_a']}")
            print(f"Contract: {opp['contract']}")
            print(f"\nTrade Strategy:")
            print(
                f"  BUY  on {opp['market_a_source'].upper():12} @ ${opp['buy_at']:.4f}"
            )
            print(
                f"  SELL on {opp['market_b_source'].upper():12} @ ${opp['sell_at']:.4f}"
            )
            print(f"\nProfit Analysis:")
            print(f"  Profit per share: ${opp['profit_per_share']:.4f}")
            print(f"  Spread: {opp['spread_pct']:.2f}%")
            print(f"\nMatch Quality:")
            print(f"  Match Score: {opp['match_score']:.3f}")
            print(f"  Confidence: {opp['confidence']}")

        # Summary
        print(f"\n{'='*80}")
        print("SUMMARY")
        print("=" * 80)
        total_profit = sum(opp["profit_per_share"] for opp in opportunities)
        avg_spread = sum(opp["spread_pct"] for opp in opportunities) / len(
            opportunities
        )
        print(f"Total Opportunities: {len(opportunities)}")
        print(f"Average Spread: {avg_spread:.2f}%")
        print(f"Total Profit (1 share each): ${total_profit:.2f}")
        print()

    finally:
        session.close()


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Find arbitrage opportunities in matched markets"
    )
    parser.add_argument(
        "--db",
        default="pm_arb_demo.db",
        help="Path to SQLite database",
    )
    parser.add_argument(
        "--min-spread",
        type=float,
        default=5.0,
        help="Minimum spread % to report (default: 5)",
    )

    args = parser.parse_args()
    find_arbitrage_opportunities(args.db, args.min_spread)


if __name__ == "__main__":
    main()
