#!/usr/bin/env python
"""
Persist matched market pairs to database.

This script finds matches using the MarketMatcher and optionally the
MatcherClassifier, then saves them to the matched_market_pairs table.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pm_arb.sql_storage import (
    init_db,
    MarketORM,
    load_market,
    save_matched_pair,
    get_matched_pairs,
    MatchedMarketPairORM,
)
from pm_arb.matcher import MarketMatcher
from pm_arb.matcher_classifier import MatcherClassifier
import argparse


def main():
    """Find matches and persist to database."""
    parser = argparse.ArgumentParser(
        description="Find and persist matched market pairs"
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
        help="Minimum rule-based match score (default: 0.5)",
    )
    parser.add_argument(
        "--use-classifier",
        action="store_true",
        help="Also compute classifier probability",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing matches before persisting new ones",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Show persisted matches",
    )

    args = parser.parse_args()

    # Initialize database
    engine, SessionLocal = init_db(f"sqlite:///{args.db}")
    session = SessionLocal()

    try:
        # Clear existing if requested
        if args.clear:
            session.query(MatchedMarketPairORM).delete()
            session.commit()
            print("Cleared existing matched pairs\n")

        # Load all markets
        market_orms = session.query(MarketORM).all()
        if not market_orms:
            print("No markets found in database. Run create_sample_markets.py first.")
            return

        markets = []
        for market_orm in market_orms:
            market = load_market(session, market_orm.source, market_orm.market_id)
            if market:
                markets.append(market)

        print(f"Loaded {len(markets)} markets\n")

        # Initialize matcher
        matcher = MarketMatcher()

        # Initialize classifier if requested
        classifier = None
        if args.use_classifier:
            classifier = MatcherClassifier()
            print("Classifier enabled (will compute probabilities)\n")

        # Find matches
        print("=" * 80)
        print("FINDING AND PERSISTING MATCHES")
        print("=" * 80 + "\n")

        matches_saved = 0

        for i, market_a in enumerate(markets):
            for market_b in markets[i + 1 :]:
                if market_a.source == market_b.source:
                    continue  # Skip same-source pairs

                # Get rule-based match
                match_result = matcher.match_single_pair(market_a, market_b)

                if match_result.match_score < args.min_score:
                    continue

                # Compute classifier probability if enabled
                classifier_prob = None
                if classifier:
                    classifier_prob = classifier.predict(market_a, market_b)

                # Persist the match
                save_matched_pair(
                    session,
                    market_a.source,
                    market_a.market_id,
                    market_b.source,
                    market_b.market_id,
                    similarity=match_result.match_score,
                    classifier_probability=classifier_prob,
                    name_similarity=match_result.name_similarity,
                    category_similarity=match_result.category_similarity,
                    temporal_proximity=match_result.temporal_proximity,
                )

                matches_saved += 1
                print(f"✓ Saved match #{matches_saved}")
                print(
                    f"  {market_a.source}/{market_a.market_id} ↔ {market_b.source}/{market_b.market_id}"
                )
                print(f"  Rule-based score: {match_result.match_score:.2%}")
                if classifier_prob:
                    print(f"  Classifier prob:  {classifier_prob:.2%}")
                print()

        print("=" * 80)
        print(f"Persisted {matches_saved} matches")
        print("=" * 80 + "\n")

        # Show persisted matches if requested
        if args.show or matches_saved > 0:
            print("=" * 80)
            print("PERSISTED MATCHED PAIRS")
            print("=" * 80 + "\n")

            pairs = get_matched_pairs(session, min_similarity=0.0)

            if not pairs:
                print("No matched pairs found in database.\n")
            else:
                for i, pair in enumerate(pairs, 1):
                    print(f"Match #{i}")
                    print(f"  Pair 1: {pair.source_a}/{pair.market_id_a}")
                    print(f"  Pair 2: {pair.source_b}/{pair.market_id_b}")
                    print(f"  Rule-based similarity: {pair.similarity:.2%}")
                    if pair.classifier_probability is not None:
                        print(
                            f"  Classifier probability: {pair.classifier_probability:.2%}"
                        )
                    print(f"  Confirmed: {'Yes' if pair.is_manual_confirmed else 'No'}")
                    if pair.notes:
                        print(f"  Notes: {pair.notes}")
                    print()

    finally:
        session.close()


if __name__ == "__main__":
    main()
