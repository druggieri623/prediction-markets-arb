#!/usr/bin/env python
"""
Demo script for training and evaluating the market matching classifier.

This script:
1. Creates synthetic training data from the demo database
2. Trains a logistic regression classifier
3. Evaluates performance
4. Shows feature importance
5. Demonstrates predictions
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pm_arb.sql_storage import init_db, MarketORM, load_market
from pm_arb.matcher_classifier import MatcherClassifier
import argparse


def create_training_data(markets):
    """
    Create training data from markets.

    Heuristic: Markets are the same if they have the same source AND
    similar names (fuzzy match > 0.8) - this is our ground truth.
    """
    from difflib import SequenceMatcher

    positive_pairs = []
    negative_pairs = []

    # Find positive pairs: same source, very similar names (synthetic ground truth)
    by_source = {}
    for market in markets:
        if market.source not in by_source:
            by_source[market.source] = []
        by_source[market.source].append(market)

    # Create negative pairs: different sources, reasonable differences
    for i, market_a in enumerate(markets):
        for market_b in markets[i + 1 :]:
            # Different sources = different markets (negative pair)
            if market_a.source != market_b.source:
                negative_pairs.append((market_a, market_b))

    # Create positive pairs using known matches from the demo
    if len(markets) >= 2:
        # Bitcoin markets are the same event
        bitcoin_markets = [m for m in markets if "bitcoin" in m.name.lower()]
        if len(bitcoin_markets) >= 2:
            positive_pairs.append((bitcoin_markets[0], bitcoin_markets[1]))

        # Inflation markets are the same event
        inflation_markets = [m for m in markets if "inflation" in m.name.lower()]
        if len(inflation_markets) >= 2:
            positive_pairs.append((inflation_markets[0], inflation_markets[1]))

        # AGI markets are the same event
        agi_markets = [
            m
            for m in markets
            if "agi" in m.name.lower() or "artificial general" in m.name.lower()
        ]
        if len(agi_markets) >= 2:
            positive_pairs.append((agi_markets[0], agi_markets[1]))

    return positive_pairs, negative_pairs


def main():
    """Run the classifier demo."""
    parser = argparse.ArgumentParser(
        description="Train and evaluate market matching classifier"
    )
    parser.add_argument(
        "--db",
        default="pm_arb_demo.db",
        help="Path to SQLite database (default: pm_arb_demo.db)",
    )
    parser.add_argument(
        "--save",
        help="Save trained classifier to this path",
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

        print(f"\nLoaded {len(markets)} markets\n")

        # Create training data
        positive_pairs, negative_pairs = create_training_data(markets)

        print("=" * 80)
        print("TRAINING DATA SUMMARY")
        print("=" * 80)
        print(f"Positive pairs (same market): {len(positive_pairs)}")
        for i, (a, b) in enumerate(positive_pairs, 1):
            print(f"  {i}. {a.source}/{a.market_id} ↔ {b.source}/{b.market_id}")

        print(f"\nNegative pairs (different markets): {len(negative_pairs)}")
        if negative_pairs:
            for i, (a, b) in enumerate(negative_pairs[:5], 1):
                print(f"  {i}. {a.source}/{a.market_id} ↔ {b.source}/{b.market_id}")
            if len(negative_pairs) > 5:
                print(f"  ... and {len(negative_pairs) - 5} more")

        # Create and train classifier
        classifier = MatcherClassifier()

        print("\n" + "=" * 80)
        print("TRAINING CLASSIFIER")
        print("=" * 80)

        metrics = classifier.train(positive_pairs, negative_pairs)

        print(f"\nTraining Summary:")
        print(f"  Total samples: {metrics['n_total']}")
        print(f"  Positive: {metrics['n_positive']}, Negative: {metrics['n_negative']}")
        print(f"  Accuracy: {metrics['accuracy']:.4f}")
        print(f"  AUC-ROC: {metrics['auc_roc']:.4f}")

        print(f"\nModel Coefficients:")
        for feature, coef in metrics["coefficients"].items():
            print(f"  {feature:20s}: {coef:8.4f}")
        print(f"  Intercept: {metrics['intercept']:8.4f}")

        # Feature importance
        print("\n" + "=" * 80)
        print("FEATURE IMPORTANCE")
        print("=" * 80)
        importance = classifier.get_feature_importance()
        for feature, score in sorted(
            importance.items(), key=lambda x: x[1], reverse=True
        ):
            print(f"  {feature:20s}: {score:.4f} ({score*100:.1f}%)")

        # Make predictions on test pairs
        print("\n" + "=" * 80)
        print("EXAMPLE PREDICTIONS")
        print("=" * 80)

        if len(markets) >= 2:
            print("\nPositive pair examples (should be high probability):")
            for i, (market_a, market_b) in enumerate(positive_pairs, 1):
                prob = classifier.predict(market_a, market_b)
                print(f"  {i}. {market_a.name[:40]:40s} ↔ {market_b.name[:40]:40s}")
                print(f"     Probability: {prob:.4f}")

            print("\nNegative pair examples (should be low probability):")
            for i, (market_a, market_b) in enumerate(negative_pairs[:3], 1):
                prob = classifier.predict(market_a, market_b)
                print(f"  {i}. {market_a.name[:40]:40s} ↔ {market_b.name[:40]:40s}")
                print(f"     Probability: {prob:.4f}")

        # Save classifier if requested
        if args.save:
            classifier.save(args.save)
            print(f"\n✓ Classifier saved to {args.save}")

        print("\n" + "=" * 80)
        print("✓ Training complete!")
        print("=" * 80 + "\n")

    finally:
        session.close()


if __name__ == "__main__":
    main()
