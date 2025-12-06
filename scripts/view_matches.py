#!/usr/bin/env python
"""
Query and display matched market pairs from database.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pm_arb.sql_storage import init_db, get_matched_pairs
import argparse


def main():
    """Display matched pairs from database."""
    parser = argparse.ArgumentParser(description="View matched market pairs")
    parser.add_argument(
        "--db",
        default="pm_arb_demo.db",
        help="Path to SQLite database (default: pm_arb_demo.db)",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        help="Minimum similarity score filter",
    )
    parser.add_argument(
        "--source-a",
        help="Filter by source A",
    )
    parser.add_argument(
        "--source-b",
        help="Filter by source B",
    )
    parser.add_argument(
        "--confirmed",
        action="store_true",
        help="Show only confirmed matches",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of results",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )

    args = parser.parse_args()

    # Initialize database
    engine, SessionLocal = init_db(f"sqlite:///{args.db}")
    session = SessionLocal()

    try:
        # Get matched pairs with filters
        min_score = args.min_score or 0.0
        pairs = get_matched_pairs(
            session,
            source_a=args.source_a,
            source_b=args.source_b,
            min_similarity=min_score,
            confirmed_only=args.confirmed,
        )

        if args.limit:
            pairs = pairs[: args.limit]

        if args.json:
            import json

            result = []
            for pair in pairs:
                result.append(
                    {
                        "source_a": pair.source_a,
                        "market_id_a": pair.market_id_a,
                        "source_b": pair.source_b,
                        "market_id_b": pair.market_id_b,
                        "similarity": round(pair.similarity, 4),
                        "classifier_probability": (
                            round(pair.classifier_probability, 4)
                            if pair.classifier_probability
                            else None
                        ),
                        "name_similarity": (
                            round(pair.name_similarity, 4)
                            if pair.name_similarity
                            else None
                        ),
                        "category_similarity": (
                            round(pair.category_similarity, 4)
                            if pair.category_similarity
                            else None
                        ),
                        "temporal_proximity": (
                            round(pair.temporal_proximity, 4)
                            if pair.temporal_proximity
                            else None
                        ),
                        "is_manual_confirmed": pair.is_manual_confirmed,
                        "confirmed_by": pair.confirmed_by,
                        "notes": pair.notes,
                        "created_at": (
                            pair.created_at.isoformat() if pair.created_at else None
                        ),
                    }
                )
            print(json.dumps(result, indent=2))
        else:
            # Text output
            print(f"\n{'=' * 100}")
            print(f"MATCHED MARKET PAIRS (Total: {len(pairs)})")
            print(f"{'=' * 100}\n")

            if not pairs:
                print("No matched pairs found.\n")
            else:
                for i, pair in enumerate(pairs, 1):
                    confirmed_badge = (
                        "✓ CONFIRMED" if pair.is_manual_confirmed else "◯ unconfirmed"
                    )
                    print(f"Match #{i} {confirmed_badge}")
                    print(f"  Market A: {pair.source_a:12s} | {pair.market_id_a}")
                    print(f"  Market B: {pair.source_b:12s} | {pair.market_id_b}")
                    print()
                    print(f"  Scores:")
                    print(f"    Overall similarity: {pair.similarity:6.2%}")
                    if pair.classifier_probability is not None:
                        print(
                            f"    Classifier prob:    {pair.classifier_probability:6.2%}"
                        )
                    if pair.name_similarity is not None:
                        print(f"    Name similarity:    {pair.name_similarity:6.2%}")
                    if pair.category_similarity is not None:
                        print(
                            f"    Category similar:   {pair.category_similarity:6.2%}"
                        )
                    if pair.temporal_proximity is not None:
                        print(f"    Temporal proximity: {pair.temporal_proximity:6.2%}")

                    if pair.is_manual_confirmed:
                        print()
                        print(f"  Confirmed by: {pair.confirmed_by}")
                        if pair.confirmed_at:
                            print(f"  Confirmed at: {pair.confirmed_at}")

                    if pair.notes:
                        print()
                        print(f"  Notes: {pair.notes}")

                    print()

    finally:
        session.close()


if __name__ == "__main__":
    main()
