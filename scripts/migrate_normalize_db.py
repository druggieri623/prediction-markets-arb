#!/usr/bin/env python3
"""Migration script: normalize existing market and contract IDs in SQLite DB.

This script reads all markets from the DB, computes normalized IDs using the
same logic as `sql_storage.save_market`, re-saves the market (which applies
normalization to contracts), and removes the old unnormalized market row
if the market_id changed.

Run from repo root with:
  PYTHONPATH=src python scripts/migrate_normalize_db.py --db pm_arb_demo.db

Use `--dry-run` to preview changes without modifying the DB.
"""
from __future__ import annotations

import argparse
import re
from typing import Optional
from unicodedata import normalize as unormalize


def normalize_id_raw(s: Optional[str], max_len: int = 128) -> Optional[str]:
    if s is None:
        return None
    s2 = unormalize("NFKC", s).strip().strip('"').strip("'")
    s2 = re.sub(r"[\x00-\x1f\r\n]", "", s2)
    s2 = re.sub(r"\s+", "_", s2)
    s2 = s2.lower()
    s2 = re.sub(r"[^a-z0-9_\-]", "", s2)
    s2 = re.sub(r"[_\-]{2,}", "_", s2)
    if max_len:
        s2 = s2[:max_len]
    return s2 or None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="pm_arb_demo.db", help="SQLite DB file")
    parser.add_argument("--dry-run", action="store_true", help="Don't write changes")
    args = parser.parse_args()

    try:
        from pm_arb import sql_storage
        from pm_arb.sql_storage import MarketORM
    except Exception:
        print("Failed to import pm_arb package. Run with PYTHONPATH=src from repo root.")
        raise

    db_url = args.db
    if not db_url.startswith("sqlite:"):
        db_url = f"sqlite:///{db_url}"

    engine, SessionLocal = sql_storage.init_db(db_url)
    session = SessionLocal()

    markets = session.query(MarketORM).order_by(MarketORM.id).all()
    changes = []
    for m in markets:
        old_id = m.market_id
        source = m.source
        print(f"Processing market id={m.id} source={source} market_id={old_id}")
        um = sql_storage.load_market(session, source, old_id)
        if not um:
            print("  could not load market, skipping")
            continue
        norm_id = normalize_id_raw(um.market_id)
        if norm_id is None:
            print("  normalized id empty, skipping")
            continue

        if norm_id == old_id:
            print("  market_id already normalized; re-saving to normalize contracts")
            if not args.dry_run:
                sql_storage.save_market(session, um)
            changes.append((old_id, norm_id))
        else:
            print(f"  will normalize market_id -> {norm_id}")
            # set the market id to normalized and save
            um.market_id = norm_id
            if not args.dry_run:
                sql_storage.save_market(session, um)
                # delete old market row (and its contracts)
                session.query(MarketORM).filter(MarketORM.source == source, MarketORM.market_id == old_id).delete()
                session.commit()
            changes.append((old_id, norm_id))

    session.close()

    print("Migration completed. Changes:")
    for old, new in changes:
        print(f"  {old} -> {new}")


if __name__ == "__main__":
    main()
