"""
Unit tests for the market matching classifier.
"""

import pytest
import numpy as np

from pm_arb.api.models import UnifiedMarket, UnifiedContract
from pm_arb.matcher_classifier import MatcherClassifier


@pytest.fixture
def classifier():
    """Create a classifier instance."""
    return MatcherClassifier()


@pytest.fixture
def sample_markets():
    """Create sample markets for testing."""
    # Bitcoin market 1 (Kalshi)
    bitcoin_kalshi = UnifiedMarket(
        source="kalshi",
        market_id="btc-1",
        name="Will Bitcoin reach $100,000 by end of 2025?",
        category="Crypto",
        event_time="2025-12-31T23:59:59Z",
        contracts=[
            UnifiedContract(
                source="kalshi",
                market_id="btc-1",
                contract_id="yes",
                name="YES",
                side="YES",
                outcome_type="binary",
            )
        ],
    )

    # Bitcoin market 2 (Polymarket) - slightly different wording, same event
    bitcoin_polymarket = UnifiedMarket(
        source="polymarket",
        market_id="btc-2",
        name="Bitcoin to exceed 100k USD before Dec 31 2025?",
        category="Crypto",
        event_time="2025-12-31T00:00:00Z",
        contracts=[
            UnifiedContract(
                source="polymarket",
                market_id="btc-2",
                contract_id="yes",
                name="Yes",
                side="Yes",
                outcome_type="binary",
            )
        ],
    )

    # Different market (Inflation)
    inflation = UnifiedMarket(
        source="kalshi",
        market_id="inf-1",
        name="Will US inflation exceed 3%?",
        category="Economy",
        event_time="2025-12-31T23:59:59Z",
        contracts=[
            UnifiedContract(
                source="kalshi",
                market_id="inf-1",
                contract_id="yes",
                name="YES",
                side="YES",
                outcome_type="binary",
            )
        ],
    )

    return {
        "bitcoin_kalshi": bitcoin_kalshi,
        "bitcoin_polymarket": bitcoin_polymarket,
        "inflation": inflation,
    }


class TestMatcherClassifier:
    """Tests for MatcherClassifier."""

    def test_initialization(self, classifier):
        """Test classifier initialization."""
        assert classifier.is_fitted is False
        assert classifier.model is not None
        assert classifier.scaler is not None

    def test_extract_features_basic(self, classifier, sample_markets):
        """Test feature extraction."""
        btc_kalshi = sample_markets["bitcoin_kalshi"]
        btc_poly = sample_markets["bitcoin_polymarket"]

        features = classifier.extract_features(btc_kalshi, btc_poly)

        assert features.shape == (1, 3)
        assert 0 <= features[0, 0] <= 1  # TFIDF similarity
        assert features[0, 1] >= 0  # Time difference (days)
        assert features[0, 2] in [0.0, 1.0]  # Category match flag

    def test_time_diff_same_date(self, classifier, sample_markets):
        """Test time difference with same date."""
        market1 = UnifiedMarket(
            source="a",
            market_id="1",
            name="Test",
            event_time="2025-12-31T12:00:00Z",
        )
        market2 = UnifiedMarket(
            source="b",
            market_id="2",
            name="Test",
            event_time="2025-12-31T14:00:00Z",
        )

        time_diff = classifier._compute_time_diff(market1, market2)
        assert time_diff == 0.0

    def test_time_diff_different_dates(self, classifier):
        """Test time difference with different dates."""
        market1 = UnifiedMarket(
            source="a",
            market_id="1",
            name="Test",
            event_time="2025-01-01T00:00:00Z",
        )
        market2 = UnifiedMarket(
            source="b",
            market_id="2",
            name="Test",
            event_time="2025-01-08T00:00:00Z",
        )

        time_diff = classifier._compute_time_diff(market1, market2)
        assert time_diff == 7.0

    def test_time_diff_missing_date(self, classifier):
        """Test time difference with missing date."""
        market1 = UnifiedMarket(
            source="a",
            market_id="1",
            name="Test",
            event_time="2025-01-01T00:00:00Z",
        )
        market2 = UnifiedMarket(
            source="b",
            market_id="2",
            name="Test",
            event_time=None,
        )

        time_diff = classifier._compute_time_diff(market1, market2)
        assert time_diff == 365.0

    def test_category_match_same(self, classifier):
        """Test category match with same category."""
        market1 = UnifiedMarket(
            source="a",
            market_id="1",
            name="Test",
            category="Crypto",
        )
        market2 = UnifiedMarket(
            source="b",
            market_id="2",
            name="Test",
            category="Crypto",
        )

        match = classifier._compute_category_match(market1, market2)
        assert match == 1.0

    def test_category_match_different(self, classifier):
        """Test category match with different categories."""
        market1 = UnifiedMarket(
            source="a",
            market_id="1",
            name="Test",
            category="Crypto",
        )
        market2 = UnifiedMarket(
            source="b",
            market_id="2",
            name="Test",
            category="Economy",
        )

        match = classifier._compute_category_match(market1, market2)
        assert match == 0.0

    def test_category_match_missing(self, classifier):
        """Test category match with missing category."""
        market1 = UnifiedMarket(
            source="a",
            market_id="1",
            name="Test",
            category="Crypto",
        )
        market2 = UnifiedMarket(
            source="b",
            market_id="2",
            name="Test",
            category=None,
        )

        match = classifier._compute_category_match(market1, market2)
        assert match == 0.0

    def test_train_basic(self, classifier, sample_markets):
        """Test basic training."""
        btc_kalshi = sample_markets["bitcoin_kalshi"]
        btc_poly = sample_markets["bitcoin_polymarket"]
        inflation = sample_markets["inflation"]

        # Positive pair: same market, different platforms
        positive_pairs = [(btc_kalshi, btc_poly)]
        # Negative pair: different markets
        negative_pairs = [(btc_kalshi, inflation)]

        metrics = classifier.train(positive_pairs, negative_pairs)

        assert classifier.is_fitted is True
        assert metrics["n_positive"] == 1
        assert metrics["n_negative"] == 1
        assert metrics["n_total"] == 2
        assert "accuracy" in metrics
        assert "auc_roc" in metrics
        assert "coefficients" in metrics
        assert "intercept" in metrics

    def test_train_with_multiple_pairs(self, classifier, sample_markets):
        """Test training with multiple pairs."""
        btc_kalshi = sample_markets["bitcoin_kalshi"]
        btc_poly = sample_markets["bitcoin_polymarket"]
        inflation = sample_markets["inflation"]

        # Create synthetic pairs (simplified)
        positive_pairs = [
            (btc_kalshi, btc_poly),
            (btc_kalshi, btc_poly),
        ]
        negative_pairs = [
            (btc_kalshi, inflation),
            (btc_poly, inflation),
        ]

        metrics = classifier.train(positive_pairs, negative_pairs)

        assert metrics["n_positive"] == 2
        assert metrics["n_negative"] == 2
        assert metrics["n_total"] == 4
        assert 0 <= metrics["accuracy"] <= 1
        assert 0 <= metrics["auc_roc"] <= 1

    def test_predict_before_training(self, classifier, sample_markets):
        """Test that predict raises error before training."""
        btc_kalshi = sample_markets["bitcoin_kalshi"]
        btc_poly = sample_markets["bitcoin_polymarket"]

        with pytest.raises(ValueError):
            classifier.predict(btc_kalshi, btc_poly)

    def test_predict_after_training(self, classifier, sample_markets):
        """Test prediction after training."""
        btc_kalshi = sample_markets["bitcoin_kalshi"]
        btc_poly = sample_markets["bitcoin_polymarket"]
        inflation = sample_markets["inflation"]

        # Train classifier
        classifier.train(
            [(btc_kalshi, btc_poly)],
            [(btc_kalshi, inflation)],
        )

        # Predict on same pair
        prob_same = classifier.predict(btc_kalshi, btc_poly)
        assert 0 <= prob_same <= 1

        # Predict on different pair
        prob_diff = classifier.predict(btc_kalshi, inflation)
        assert 0 <= prob_diff <= 1

    def test_predict_batch(self, classifier, sample_markets):
        """Test batch predictions."""
        btc_kalshi = sample_markets["bitcoin_kalshi"]
        btc_poly = sample_markets["bitcoin_polymarket"]
        inflation = sample_markets["inflation"]

        # Train
        classifier.train(
            [(btc_kalshi, btc_poly)],
            [(btc_kalshi, inflation)],
        )

        # Batch predict
        pairs = [
            (btc_kalshi, btc_poly),
            (btc_kalshi, inflation),
        ]
        probs = classifier.predict_batch(pairs)

        assert len(probs) == 2
        assert all(0 <= p <= 1 for p in probs)

    def test_get_feature_importance(self, classifier, sample_markets):
        """Test feature importance calculation."""
        btc_kalshi = sample_markets["bitcoin_kalshi"]
        btc_poly = sample_markets["bitcoin_polymarket"]
        inflation = sample_markets["inflation"]

        # Train
        classifier.train(
            [(btc_kalshi, btc_poly)],
            [(btc_kalshi, inflation)],
        )

        # Get importance
        importance = classifier.get_feature_importance()

        assert "tfidf_sim" in importance
        assert "time_diff" in importance
        assert "category_match" in importance
        assert all(0 <= v <= 1 for v in importance.values())
        assert abs(sum(importance.values()) - 1.0) < 0.01  # Sum to 1

    def test_save_and_load(self, classifier, sample_markets, tmp_path):
        """Test saving and loading classifier."""
        btc_kalshi = sample_markets["bitcoin_kalshi"]
        btc_poly = sample_markets["bitcoin_polymarket"]
        inflation = sample_markets["inflation"]

        # Train
        classifier.train(
            [(btc_kalshi, btc_poly)],
            [(btc_kalshi, inflation)],
        )

        # Save
        filepath = tmp_path / "classifier.pkl"
        classifier.save(str(filepath))
        assert filepath.exists()

        # Load into new classifier
        classifier2 = MatcherClassifier()
        classifier2.load(str(filepath))

        # Predictions should match
        prob1 = classifier.predict(btc_kalshi, btc_poly)
        prob2 = classifier2.predict(btc_kalshi, btc_poly)
        assert abs(prob1 - prob2) < 1e-6

    def test_save_before_training(self, classifier):
        """Test that save raises error before training."""
        with pytest.raises(ValueError):
            classifier.save("/tmp/test.pkl")
