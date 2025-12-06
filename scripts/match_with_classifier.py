#!/usr/bin/env python
"""
Demo script showing market matching with ML classifier.

This shows how to:
1. Train the classifier on known matches
2. Use it to predict which pairs are likely the same market
3. Compare classifier predictions with rule-based matcher scores
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pm_arb.sql_storage import init_db, MarketORM, load_market
from pm_arb.matcher import MarketMatcher
from pm_arb.matcher_classifier import MatcherClassifier
import argparse


def main():
    """Run market matching with classifier."""
    parser = argparse.ArgumentParser(
        description="Find market matches using ML classifier"
    )
    parser.add_argument(
        "--db",
        default="pm_arb_demo.db",
        help="Path to SQLite database (default: pm_arb_demo.db)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Probability threshold for match (default: 0.5)",
    )

    args = parser.parse_args()

    # Initialize database
    engine, SessionLocal = init_db(f"sqlite:///{args.db}")
    session = SessionLocal()

    try:
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

        print(f"\n{'=' * 90}")
        print(f"Loaded {len(markets)} markets from database")
        print(f"{'=' * 90}\n")

        # Initialize matcher and classifier
        matcher = MarketMatcher()
        classifier = MatcherClassifier()

        # Create synthetic training data
        print("Training classifier on sample data...")

        positive_pairs = []
        negative_pairs = []

        # Same-source pairs (ground truth: different markets)
        for i, market_a in enumerate(markets):
            for market_b in markets[i + 1 :]:
                if market_a.source != market_b.source:
                    # Cross-source pairs are candidates for matching
                    negative_pairs.append((market_a, market_b))

        # Create positive pairs from known matches
        bitcoin_markets = [m for m in markets if "bitcoin" in m.name.lower()]
        if len(bitcoin_markets) >= 2:
            positive_pairs.append((bitcoin_markets[0], bitcoin_markets[1]))

        inflation_markets = [m for m in markets if "inflation" in m.name.lower()]
        if len(inflation_markets) >= 2:
            positive_pairs.append((inflation_markets[0], inflation_markets[1]))

        agi_markets = [
            m
            for m in markets
            if "agi" in m.name.lower() or "artificial general" in m.name.lower()
        ]
        if len(agi_markets) >= 2:
            positive_pairs.append((agi_markets[0], agi_markets[1]))

        # Train classifier
        metrics = classifier.train(positive_pairs, negative_pairs)
        print(f"  Accuracy: {metrics['accuracy']:.2%}")
        print(f"  AUC-ROC: {metrics['auc_roc']:.4f}\n")

        # Find matches using classifier
        print(f"{'=' * 90}")
        print(f"MARKET MATCHES (using ML classifier, threshold={args.threshold})")
        print(f"{'=' * 90}\n")

        matches_found = 0
        for i, market_a in enumerate(markets):
            for market_b in markets[i + 1 :]:
                if market_a.source != market_b.source:
                    # Get classifier prediction
                    prob = classifier.predict(market_a, market_b)

                    # Get rule-based matcher score
                    match_result = matcher.match_single_pair(market_a, market_b)

                    if prob >= args.threshold:
                        matches_found += 1
                        print(f"Match #{matches_found}")
                        print(
                            f"  Source 1: {market_a.source:12s} | {market_a.name[:50]}"
                        )
                        print(
                            f"  Source 2: {market_b.source:12s} | {market_b.name[:50]}"
                        )
                        print(f"  ")
                        print(f"  Classifier Probability: {prob:6.2%}")
                        print(
                            f"  Rule-based Score:       {match_result.match_score:6.2%}"
                        )
                        print(
                            f"    - Name similarity:     {match_result.name_similarity:6.2%}"
                        )
                        print(
                            f"    - Category similarity: {match_result.category_similarity:6.2%}"
                        )
                        print(
                            f"    - Temporal similarity: {match_result.temporal_proximity:6.2%}"
                        )
                        print(f"  ")
                        print(f"  Confidence: {match_result.confidence}")
                        print()

        if matches_found == 0:
            print("No matches found at this threshold.")
            print(f"Try lowering --threshold (current: {args.threshold})")

        print(f"{'=' * 90}")
        print(f"Summary: Found {matches_found} matches")
        print(f"{'=' * 90}\n")

    finally:
        session.close()


if __name__ == "__main__":
    main()
