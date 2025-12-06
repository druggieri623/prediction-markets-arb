#!/usr/bin/env python
"""
Demo script showing market matching across platforms.

This script:
1. Loads markets from the demo DB (from multiple platforms)
2. Runs the ML-based matcher to find cross-platform matches
3. Displays results with confidence levels and scores
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pm_arb.sql_storage import init_db, load_market
from pm_arb.matcher import MarketMatcher
import argparse


def main():
    """Run market matching demo."""
    parser = argparse.ArgumentParser(
        description="Find matching markets across prediction platforms"
    )
    parser.add_argument(
        "--db",
        default="pm_arb_demo.db",
        help="Path to SQLite database (default: pm_arb_demo.db)",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=0.5,
        help="Minimum match score to display (0-1, default: 0.5)",
    )
    parser.add_argument(
        "--show-contracts",
        action="store_true",
        help="Show matching contracts for each match",
    )
    parser.add_argument(
        "--min-confidence",
        choices=["low", "medium", "high"],
        default="low",
        help="Minimum confidence level to display",
    )

    args = parser.parse_args()

    # Initialize database
    engine, SessionLocal = init_db(f"sqlite:///{args.db}")
    session = SessionLocal()

    try:
        # Load all markets from DB
        from pm_arb.sql_storage import MarketORM

        market_orms = session.query(MarketORM).all()
        print(f"\nLoaded {len(market_orms)} markets from {args.db}\n")

        if not market_orms:
            print("No markets found in database. Run demo_fetch.py first.")
            return

        # Convert ORM models to unified models
        from pm_arb.sql_storage import load_market

        markets = []
        for market_orm in market_orms:
            market = load_market(session, market_orm.source, market_orm.market_id)
            if market:
                markets.append(market)

        print(f"Successfully converted {len(markets)} markets\n")

        # Initialize matcher
        matcher = MarketMatcher(
            name_weight=0.4,
            category_weight=0.2,
            contract_weight=0.3,
            temporal_weight=0.1,
            min_score_threshold=args.min_score,
        )

        # Find matches across platforms
        print("=" * 80)
        print("MARKET MATCHING RESULTS")
        print("=" * 80)

        matches = matcher.find_matches(markets, cross_source_only=True)

        # Filter by confidence level
        confidence_levels = {"low": 0, "medium": 1, "high": 2}
        min_confidence_level = confidence_levels[args.min_confidence]

        filtered_matches = [
            m
            for m in matches
            if confidence_levels.get(m.confidence, 0) >= min_confidence_level
        ]

        print(f"\nFound {len(matches)} potential matches")
        print(
            f"Filtered to {len(filtered_matches)} matches with {args.min_confidence}+ confidence\n"
        )

        if not filtered_matches:
            print("No matches found above the threshold.")
            return

        # Display results
        for i, match in enumerate(filtered_matches, 1):
            print(f"\n{i}. Match #{i}")
            print("-" * 80)

            # Market A
            print(f"   Market A: {match.market_a.source.upper()}")
            print(f"   ID: {match.market_a.market_id}")
            print(f"   Name: {match.market_a.name}")
            if match.market_a.category:
                print(f"   Category: {match.market_a.category}")
            if match.market_a.event_time:
                print(f"   Event Time: {match.market_a.event_time}")
            print(f"   Contracts: {len(match.market_a.contracts)}")

            # Market B
            print(f"\n   Market B: {match.market_b.source.upper()}")
            print(f"   ID: {match.market_b.market_id}")
            print(f"   Name: {match.market_b.name}")
            if match.market_b.category:
                print(f"   Category: {match.market_b.category}")
            if match.market_b.event_time:
                print(f"   Event Time: {match.market_b.event_time}")
            print(f"   Contracts: {len(match.market_b.contracts)}")

            # Match scores
            print(f"\n   MATCH SCORES:")
            print(f"   Overall Score: {match.match_score:.3f}")
            print(f"   Confidence: {match.confidence.upper()}")
            print(f"   Name Similarity: {match.name_similarity:.3f}")
            print(f"   Category Similarity: {match.category_similarity:.3f}")
            print(f"   Contract Similarity: {match.contract_similarity:.3f}")
            print(f"   Temporal Proximity: {match.temporal_proximity:.3f}")

            # Matching contracts
            if match.matching_contracts:
                print(f"\n   MATCHING CONTRACTS ({len(match.matching_contracts)}):")
                for contract_a, contract_b in match.matching_contracts:
                    print(
                        f"   - {contract_a.name} ({contract_a.source}) <-> "
                        f"{contract_b.name} ({contract_b.source})"
                    )
            elif args.show_contracts:
                print(f"\n   No matching contracts found")

            if match.notes:
                print(f"\n   Notes: {match.notes}")

        # Summary statistics
        print(f"\n\n{'='*80}")
        print("SUMMARY")
        print("=" * 80)
        print(f"Total Markets: {len(markets)}")
        print(f"Total Matches Found: {len(matches)}")
        print(
            f"High Confidence Matches: {sum(1 for m in matches if m.confidence == 'high')}"
        )
        print(
            f"Medium Confidence Matches: {sum(1 for m in matches if m.confidence == 'medium')}"
        )
        print(
            f"Low Confidence Matches: {sum(1 for m in matches if m.confidence == 'low')}"
        )

        if filtered_matches:
            avg_score = sum(m.match_score for m in filtered_matches) / len(
                filtered_matches
            )
            print(f"Average Match Score (filtered): {avg_score:.3f}")

    finally:
        session.close()


if __name__ == "__main__":
    main()
