#!/usr/bin/env python3
"""Reset the demo DB: drop all tables and recreate them.

Run from repo root with:
  PYTHONPATH=src python scripts/reset_demo_db.py --db pm_arb_demo.db

After resetting, run the demo to repopulate:
  python -m src.pm_arb.api.demo_fetch
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset demo SQLite DB")
    parser.add_argument(
        "--db", default="pm_arb_demo.db", help="SQLite DB file to reset"
    )
    parser.add_argument(
        "--force", action="store_true", help="Don't ask for confirmation"
    )
    args = parser.parse_args()

    db_path = Path(args.db)

    # Check if file exists
    if db_path.exists():
        if not args.force:
            response = input(f"Delete {db_path}? (y/N) ")
            if response.lower() != "y":
                print("Cancelled.")
                return
        print(f"Deleting {db_path}...")
        db_path.unlink()
    else:
        print(f"{db_path} does not exist; nothing to delete.")

    # Recreate empty DB by initializing
    try:
        from pm_arb import sql_storage
    except Exception:
        print(
            "Failed to import pm_arb package. Run with PYTHONPATH=src from repo root."
        )
        raise

    db_url = args.db
    if not db_url.startswith("sqlite:"):
        db_url = f"sqlite:///{db_url}"

    print(f"Creating fresh DB at {db_url}...")
    engine, SessionLocal = sql_storage.init_db(db_url)
    session = SessionLocal()
    session.close()

    print(f"DB reset complete. File: {db_path}")
    print("Now run: python -m src.pm_arb.api.demo_fetch")


if __name__ == "__main__":
    main()
