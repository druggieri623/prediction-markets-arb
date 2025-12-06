#!/usr/bin/env python
"""CLI tool to find arbitrage opportunities in matched market pairs."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import argparse
import json
from typing import Optional

from pm_arb.sql_storage import init_db, MarketORM
from pm_arb.arbitrage_detector import ArbitrageDetector, ArbitrageOpportunity
from pm_arb.api.models import UnifiedMarket, UnifiedContract


def find_arbitrage_opportunities(
    db_path: str = "pm_arb.db",
    min_similarity: float = 0.70,
    min_profit: float = 0.01,
    min_roi_pct: float = 0.0,
    output_format: str = "text",
    limit: int = 10,
    fetch_fresh: bool = False,
    show_details: bool = False,
) -> None:
    """Find and display arbitrage opportunities.

    Args:
        db_path: Path to SQLite database
        min_similarity: Minimum match similarity threshold [0, 1]
        min_profit: Minimum profit to flag opportunity (dollars)
        min_roi_pct: Minimum ROI percentage
        output_format: Output format ("text" or "json")
        limit: Maximum number of opportunities to show
        fetch_fresh: Fetch fresh market data before analysis
        show_details: Show detailed contract information
    """
    # Initialize database
    db_url = f"sqlite:///{db_path}"
    engine, session_factory = init_db(db_url)
    session = session_factory()

    if fetch_fresh:
        print("Fetching fresh market data...")
        from pm_arb.api.demo_fetch import main as fetch_demo
        fetch_demo(no_save=False)

    # Initialize detector
    detector = ArbitrageDetector(
        min_similarity=min_similarity,
        min_profit_threshold=min_profit,
    )

    # Load markets from database
    markets_orm = session.query(MarketORM).all()
    markets = [_orm_to_unified(m) for m in markets_orm]

    if not markets:
        print("No markets in database. Run with --fetch to load data.")
        return

    print(f"Loaded {len(markets)} markets")

    detector.register_markets(markets)

    # Detect opportunities
    print(f"Analyzing matched pairs (min similarity: {min_similarity:.0%})...")
    opportunities = detector.detect_opportunities(
        session, min_similarity=min_similarity
    )

    # Filter by additional criteria
    opportunities = [
        o
        for o in opportunities
        if o.min_profit >= min_profit and o.roi_pct >= min_roi_pct
    ]

    # Sort by profit and limit
    opportunities.sort(key=lambda x: x.min_profit, reverse=True)
    opportunities = opportunities[:limit]

    # Display results
    if output_format == "json":
        _output_json(opportunities)
    else:
        _output_text(opportunities, show_details)

    # Print summary
    print("\n" + "=" * 70)
    print(detector.summarize_opportunities(opportunities[:3]))

    session.close()


def _orm_to_unified(market_orm):
    """Convert ORM market to unified model."""
    contracts = []
    for c_orm in market_orm.contracts:
        contract = UnifiedContract(
            source=market_orm.source,
            market_id=market_orm.market_id,
            contract_id=c_orm.contract_id,
            name=c_orm.name,
            side=c_orm.side,
            outcome_type=c_orm.outcome_type,
            price_bid=c_orm.price_bid,
            price_ask=c_orm.price_ask,
            last_price=c_orm.last_price,
            volume=c_orm.volume,
            open_interest=c_orm.open_interest,
            extra=c_orm.extra,
        )
        contracts.append(contract)

    market = UnifiedMarket(
        source=market_orm.source,
        market_id=market_orm.market_id,
        name=market_orm.name,
        event_time=market_orm.event_time,
        category=market_orm.category,
        contracts=contracts,
        extra=market_orm.extra,
    )

    return market


def _output_text(opportunities, show_details: bool = False) -> None:
    """Output opportunities in text format."""
    if not opportunities:
        print("\n⊘ No profitable arbitrage opportunities found.")
        return

    print(f"\n{'='*70}")
    print(f"FOUND {len(opportunities)} ARBITRAGE OPPORTUNITIES")
    print(f"{'='*70}\n")

    for i, opp in enumerate(opportunities, 1):
        print(f"{i}. {opp.source_a.upper()}/{opp.market_id_a} ↔ {opp.source_b.upper()}/{opp.market_id_b}")
        print(f"   Type: {opp.arbitrage_type.upper()}")
        print(f"   Match Quality: {opp.match_similarity:.1%}")
        print(f"   Min Profit: ${opp.min_profit:.4f} | Max Profit: ${opp.max_profit:.4f}")
        print(f"   ROI: {opp.roi_pct:.2f}% | Investment: ${opp.total_investment:.4f}")

        if opp.is_arbitrage:
            print(f"   ✓ RISK-FREE PROFIT")
        elif opp.is_scalp:
            print(f"   ⚠ CONDITIONAL PROFIT")

        if opp.notes:
            print(f"   Strategy: {opp.notes}")

        if show_details:
            print(f"\n   YES Contract (Market A): ${opp.yes_contract_a.price_ask:.4f}")
            print(f"   NO Contract (Market A): ${opp.no_contract_a.price_ask:.4f}")
            print(f"   YES Contract (Market B): ${opp.yes_contract_b.price_ask:.4f}")
            print(f"   NO Contract (Market B): ${opp.no_contract_b.price_ask:.4f}")

        print()


def _output_json(opportunities) -> None:
    """Output opportunities in JSON format."""
    data = {
        "count": len(opportunities),
        "opportunities": [
            {
                "source_a": opp.source_a,
                "market_id_a": opp.market_id_a,
                "source_b": opp.source_b,
                "market_id_b": opp.market_id_b,
                "arbitrage_type": opp.arbitrage_type,
                "match_similarity": opp.match_similarity,
                "profit_if_yes": float(opp.profit_if_yes),
                "profit_if_no": float(opp.profit_if_no),
                "min_profit": float(opp.min_profit),
                "max_profit": float(opp.max_profit),
                "roi_pct": opp.roi_pct,
                "total_investment": float(opp.total_investment),
                "is_arbitrage": opp.is_arbitrage,
                "is_scalp": opp.is_scalp,
                "notes": opp.notes,
            }
            for opp in opportunities
        ],
    }

    print(json.dumps(data, indent=2))


def main():
    """Parse arguments and run arbitrage detector."""
    parser = argparse.ArgumentParser(
        description="Find arbitrage opportunities in matched market pairs"
    )
    parser.add_argument(
        "--db",
        type=str,
        default="pm_arb.db",
        help="Path to SQLite database (default: pm_arb.db)",
    )
    parser.add_argument(
        "--min-similarity",
        type=float,
        default=0.70,
        help="Minimum match similarity threshold [0, 1] (default: 0.70)",
    )
    parser.add_argument(
        "--min-profit",
        type=float,
        default=0.01,
        help="Minimum profit in dollars (default: $0.01)",
    )
    parser.add_argument(
        "--min-roi",
        type=float,
        default=0.0,
        help="Minimum ROI percentage (default: 0.0)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of opportunities to show (default: 10)",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--fetch",
        action="store_true",
        help="Fetch fresh market data before analysis",
    )
    parser.add_argument(
        "--details",
        action="store_true",
        help="Show detailed contract prices",
    )

    args = parser.parse_args()

    find_arbitrage_opportunities(
        db_path=args.db,
        min_similarity=args.min_similarity,
        min_profit=args.min_profit,
        min_roi_pct=args.min_roi,
        output_format=args.format,
        limit=args.limit,
        fetch_fresh=args.fetch,
        show_details=args.details,
    )


if __name__ == "__main__":
    main()
