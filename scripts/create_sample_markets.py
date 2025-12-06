#!/usr/bin/env python
"""
Create sample matching test data in the database.

This script adds carefully crafted similar markets from different sources
to demonstrate the matching capabilities.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pm_arb.api.models import UnifiedMarket, UnifiedContract
from pm_arb.sql_storage import init_db, save_market


def create_sample_markets():
    """Create sample markets designed to match across platforms."""

    # Bitcoin price markets (should match across platforms)
    kalshi_bitcoin = UnifiedMarket(
        source="kalshi",
        market_id="bitcoin-price-eoy-2025",
        name="Will Bitcoin close above $100,000 on Dec 31, 2025?",
        category="Crypto",
        event_time="2025-12-31T23:59:59Z",
        contracts=[
            UnifiedContract(
                source="kalshi",
                market_id="bitcoin-price-eoy-2025",
                contract_id="yes",
                name="YES",
                side="YES",
                outcome_type="binary",
                price_bid=0.65,
                price_ask=0.70,
            ),
            UnifiedContract(
                source="kalshi",
                market_id="bitcoin-price-eoy-2025",
                contract_id="no",
                name="NO",
                side="NO",
                outcome_type="binary",
                price_bid=0.30,
                price_ask=0.35,
            ),
        ],
    )

    polymarket_bitcoin = UnifiedMarket(
        source="polymarket",
        market_id="0xabc123bitcoin",
        name="Bitcoin to exceed $100k USD before end of 2025?",
        category="Cryptocurrency",
        event_time="2025-12-31T23:59:59Z",
        contracts=[
            UnifiedContract(
                source="polymarket",
                market_id="0xabc123bitcoin",
                contract_id="yes",
                name="Yes",
                side="Yes",
                outcome_type="binary",
                price_bid=0.64,
                price_ask=0.71,
            ),
            UnifiedContract(
                source="polymarket",
                market_id="0xabc123bitcoin",
                contract_id="no",
                name="No",
                side="No",
                outcome_type="binary",
                price_bid=0.29,
                price_ask=0.36,
            ),
        ],
    )

    # US Inflation markets (should match)
    kalshi_inflation = UnifiedMarket(
        source="kalshi",
        market_id="us-inflation-2025",
        name="Will US inflation (CPI YoY) exceed 3% in 2025?",
        category="Economy",
        event_time="2025-12-31T23:59:59Z",
        contracts=[
            UnifiedContract(
                source="kalshi",
                market_id="us-inflation-2025",
                contract_id="yes",
                name="YES",
                side="YES",
                outcome_type="binary",
                price_bid=0.35,
                price_ask=0.42,
            ),
            UnifiedContract(
                source="kalshi",
                market_id="us-inflation-2025",
                contract_id="no",
                name="NO",
                side="NO",
                outcome_type="binary",
                price_bid=0.58,
                price_ask=0.65,
            ),
        ],
    )

    predictit_inflation = UnifiedMarket(
        source="predictit",
        market_id="5012",
        name="Will average inflation be above 3 percent in 2025?",
        category="Economy",
        event_time="2025-12-31T23:59:59Z",
        contracts=[
            UnifiedContract(
                source="predictit",
                market_id="5012",
                contract_id="yes",
                name="Yes",
                side="Yes",
                outcome_type="binary",
                price_bid=0.34,
                price_ask=0.43,
            ),
            UnifiedContract(
                source="predictit",
                market_id="5012",
                contract_id="no",
                name="No",
                side="No",
                outcome_type="binary",
                price_bid=0.57,
                price_ask=0.66,
            ),
        ],
    )

    # AI milestone market
    polymarket_ai = UnifiedMarket(
        source="polymarket",
        market_id="0xdef456ai",
        name="Will AGI be achieved by end of 2026?",
        category="Technology",
        event_time="2026-12-31T23:59:59Z",
        contracts=[
            UnifiedContract(
                source="polymarket",
                market_id="0xdef456ai",
                contract_id="yes",
                name="Yes",
                side="Yes",
                outcome_type="binary",
                price_bid=0.05,
                price_ask=0.08,
            ),
            UnifiedContract(
                source="polymarket",
                market_id="0xdef456ai",
                contract_id="no",
                name="No",
                side="No",
                outcome_type="binary",
                price_bid=0.92,
                price_ask=0.95,
            ),
        ],
    )

    kalshi_ai = UnifiedMarket(
        source="kalshi",
        market_id="agi-by-2026",
        name="Artificial General Intelligence created by Dec 31, 2026?",
        category="Technology",
        event_time="2026-12-31T23:59:59Z",
        contracts=[
            UnifiedContract(
                source="kalshi",
                market_id="agi-by-2026",
                contract_id="yes",
                name="YES",
                side="YES",
                outcome_type="binary",
                price_bid=0.06,
                price_ask=0.09,
            ),
            UnifiedContract(
                source="kalshi",
                market_id="agi-by-2026",
                contract_id="no",
                name="NO",
                side="NO",
                outcome_type="binary",
                price_bid=0.91,
                price_ask=0.94,
            ),
        ],
    )

    return [
        kalshi_bitcoin,
        polymarket_bitcoin,
        kalshi_inflation,
        predictit_inflation,
        polymarket_ai,
        kalshi_ai,
    ]


def main():
    """Add sample markets to database."""
    import argparse

    parser = argparse.ArgumentParser(description="Create sample matching test data")
    parser.add_argument(
        "--db",
        default="pm_arb_demo.db",
        help="Path to SQLite database",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset database before adding samples",
    )

    args = parser.parse_args()

    # Initialize database
    engine, SessionLocal = init_db(f"sqlite:///{args.db}")
    session = SessionLocal()

    try:
        if args.reset:
            from pm_arb.sql_storage import MarketORM, ContractORM

            print("Resetting database...")
            session.query(ContractORM).delete()
            session.query(MarketORM).delete()
            session.commit()

        # Create and save sample markets
        markets = create_sample_markets()

        print(f"\nAdding {len(markets)} sample markets to {args.db}...")
        for market in markets:
            save_market(session, market)
            print(f"  ✓ {market.source}/{market.market_id}: {market.name}")

        session.commit()
        print(f"\n✓ Successfully added {len(markets)} sample markets\n")

        # Show what we added
        from pm_arb.sql_storage import MarketORM

        count_by_source = (
            session.query(MarketORM.source, MarketORM).group_by(MarketORM.source).all()
        )

        print("Summary by source:")
        for source, _ in count_by_source:
            count = session.query(MarketORM).filter_by(source=source).count()
            print(f"  {source.upper()}: {count} markets")

    finally:
        session.close()


if __name__ == "__main__":
    main()
