"""Tests for matched market pair storage."""

import pytest
from datetime import datetime, UTC
from pm_arb.sql_storage import (
    init_db,
    save_market,
    save_matched_pair,
    confirm_matched_pair,
    get_matched_pairs,
    MatchedMarketPairORM,
)
from pm_arb.api.models import UnifiedMarket


@pytest.fixture
def temp_db():
    """Create a temporary in-memory database."""
    engine, SessionLocal = init_db("sqlite:///:memory:")
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def sample_markets(temp_db):
    """Create sample markets for testing."""
    bitcoin_kalshi = UnifiedMarket(
        source="kalshi",
        market_id="btc-1",
        name="Will Bitcoin close above $100,000 on Dec 31?",
        event_time="2025-12-31T23:59:59Z",
        category="Crypto",
        contracts=[],
    )

    bitcoin_polymarket = UnifiedMarket(
        source="polymarket",
        market_id="0xabc123",
        name="Bitcoin to exceed $100k USD before end of 2025",
        event_time="2025-12-31T23:59:59Z",
        category="Cryptocurrency",
        contracts=[],
    )

    inflation_kalshi = UnifiedMarket(
        source="kalshi",
        market_id="inf-1",
        name="Will US inflation (CPI YoY) exceed 3% in 2025?",
        event_time="2025-12-31T23:59:59Z",
        category="Economics",
        contracts=[],
    )

    save_market(temp_db, bitcoin_kalshi)
    save_market(temp_db, bitcoin_polymarket)
    save_market(temp_db, inflation_kalshi)

    return {
        "bitcoin_kalshi": bitcoin_kalshi,
        "bitcoin_polymarket": bitcoin_polymarket,
        "inflation_kalshi": inflation_kalshi,
    }


class TestMatchedMarketPair:
    """Test matched market pair storage."""

    def test_save_matched_pair(self, temp_db, sample_markets):
        """Test saving a matched pair."""
        pair = save_matched_pair(
            temp_db,
            "kalshi",
            "btc-1",
            "polymarket",
            "0xabc123",
            similarity=0.75,
            classifier_probability=0.82,
            name_similarity=0.65,
            category_similarity=0.85,
            temporal_proximity=1.0,
        )

        assert pair.source_a == "kalshi"
        assert pair.market_id_a == "btc-1"
        assert pair.source_b == "polymarket"
        assert pair.market_id_b == "0xabc123"
        assert pair.similarity == 0.75
        assert pair.classifier_probability == 0.82
        assert pair.is_manual_confirmed == False

    def test_pair_ordering_consistency(self, temp_db, sample_markets):
        """Test that pair ordering is consistent regardless of input order."""
        # Save in one order
        pair1 = save_matched_pair(
            temp_db,
            "polymarket",
            "0xabc123",
            "kalshi",
            "btc-1",
            similarity=0.75,
        )

        # Query with opposite order - should find the same pair
        pairs = get_matched_pairs(temp_db)
        assert len(pairs) == 1

        # The pair should be stored in sorted order
        assert (pair1.source_a, pair1.market_id_a) < (pair1.source_b, pair1.market_id_b)

    def test_update_matched_pair(self, temp_db, sample_markets):
        """Test updating an existing matched pair."""
        # Save initial pair
        save_matched_pair(
            temp_db,
            "kalshi",
            "btc-1",
            "polymarket",
            "0xabc123",
            similarity=0.70,
        )

        # Update the same pair with new data
        updated_pair = save_matched_pair(
            temp_db,
            "kalshi",
            "btc-1",
            "polymarket",
            "0xabc123",
            similarity=0.80,
            classifier_probability=0.85,
            notes="Updated match score",
        )

        # Should have only one pair
        pairs = get_matched_pairs(temp_db)
        assert len(pairs) == 1

        # Similarity should be updated
        assert pairs[0].similarity == 0.80
        assert pairs[0].classifier_probability == 0.85
        assert pairs[0].notes == "Updated match score"

    def test_confirm_matched_pair(self, temp_db, sample_markets):
        """Test manual confirmation of a matched pair."""
        # Save a pair
        save_matched_pair(
            temp_db,
            "kalshi",
            "btc-1",
            "polymarket",
            "0xabc123",
            similarity=0.75,
        )

        # Confirm it
        confirmed = confirm_matched_pair(
            temp_db,
            "kalshi",
            "btc-1",
            "polymarket",
            "0xabc123",
            confirmed_by="alice@example.com",
            notes="Verified on chain",
        )

        assert confirmed is not None
        assert confirmed.is_manual_confirmed == True
        assert confirmed.confirmed_by == "alice@example.com"
        assert confirmed.notes == "Verified on chain"
        assert confirmed.confirmed_at is not None

    def test_confirm_nonexistent_pair(self, temp_db):
        """Test confirming a pair that doesn't exist."""
        result = confirm_matched_pair(
            temp_db,
            "kalshi",
            "nonexistent",
            "polymarket",
            "nothere",
        )

        assert result is None

    def test_get_matched_pairs_no_filter(self, temp_db, sample_markets):
        """Test getting all matched pairs without filters."""
        # Save multiple pairs
        save_matched_pair(
            temp_db, "kalshi", "btc-1", "polymarket", "0xabc123", similarity=0.75
        )
        save_matched_pair(
            temp_db, "kalshi", "inf-1", "polymarket", "0xdef456", similarity=0.60
        )

        pairs = get_matched_pairs(temp_db)
        assert len(pairs) == 2

    def test_get_matched_pairs_min_similarity_filter(self, temp_db, sample_markets):
        """Test filtering matched pairs by minimum similarity."""
        save_matched_pair(
            temp_db, "kalshi", "btc-1", "polymarket", "0xabc123", similarity=0.75
        )
        save_matched_pair(
            temp_db, "kalshi", "inf-1", "polymarket", "0xdef456", similarity=0.60
        )

        # Get only high-similarity pairs
        pairs = get_matched_pairs(temp_db, min_similarity=0.70)
        assert len(pairs) == 1
        assert pairs[0].similarity == 0.75

    def test_get_matched_pairs_source_filter(self, temp_db, sample_markets):
        """Test filtering matched pairs by source."""
        save_matched_pair(
            temp_db, "kalshi", "btc-1", "polymarket", "0xabc123", similarity=0.75
        )
        save_matched_pair(
            temp_db, "kalshi", "inf-1", "polymarket", "0xdef456", similarity=0.60
        )

        # Get pairs from kalshi
        pairs = get_matched_pairs(temp_db, source_a="kalshi")
        assert len(pairs) == 2
        assert all(p.source_a == "kalshi" for p in pairs)

    def test_get_matched_pairs_confirmed_only(self, temp_db, sample_markets):
        """Test filtering to only confirmed pairs."""
        # Save two pairs
        save_matched_pair(
            temp_db, "kalshi", "btc-1", "polymarket", "0xabc123", similarity=0.75
        )
        save_matched_pair(
            temp_db, "kalshi", "inf-1", "polymarket", "0xdef456", similarity=0.60
        )

        # Confirm only the first one
        confirm_matched_pair(temp_db, "kalshi", "btc-1", "polymarket", "0xabc123")

        # Get only confirmed pairs
        confirmed = get_matched_pairs(temp_db, confirmed_only=True)
        assert len(confirmed) == 1
        assert confirmed[0].similarity == 0.75

    def test_matched_pairs_ordering(self, temp_db, sample_markets):
        """Test that matched pairs are ordered by similarity descending."""
        save_matched_pair(
            temp_db, "kalshi", "btc-1", "polymarket", "0xabc123", similarity=0.60
        )
        save_matched_pair(
            temp_db, "kalshi", "inf-1", "polymarket", "0xdef456", similarity=0.85
        )
        save_matched_pair(
            temp_db, "kalshi", "abc", "polymarket", "0xghi", similarity=0.70
        )

        pairs = get_matched_pairs(temp_db)

        # Should be ordered by similarity descending
        assert pairs[0].similarity == 0.85
        assert pairs[1].similarity == 0.70
        assert pairs[2].similarity == 0.60

    def test_matched_pair_timestamps(self, temp_db, sample_markets):
        """Test that created_at and updated_at timestamps are set."""
        before = datetime.now(UTC)
        pair = save_matched_pair(
            temp_db, "kalshi", "btc-1", "polymarket", "0xabc123", similarity=0.75
        )
        after = datetime.now(UTC)

        assert before <= pair.created_at <= after
        assert before <= pair.updated_at <= after

    def test_matched_pair_update_timestamp(self, temp_db, sample_markets):
        """Test that updated_at changes when pair is updated."""
        pair = save_matched_pair(
            temp_db, "kalshi", "btc-1", "polymarket", "0xabc123", similarity=0.75
        )

        initial_updated_at = pair.updated_at

        # Update the pair
        import time

        time.sleep(0.01)  # Ensure time difference

        updated_pair = save_matched_pair(
            temp_db, "kalshi", "btc-1", "polymarket", "0xabc123", similarity=0.80
        )

        assert updated_pair.updated_at > initial_updated_at
