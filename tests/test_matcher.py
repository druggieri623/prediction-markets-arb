"""
Unit tests for the market matcher module.
"""

import pytest
from datetime import datetime

from pm_arb.api.models import UnifiedMarket, UnifiedContract
from pm_arb.matcher import MarketMatcher, MatchResult


@pytest.fixture
def sample_contract():
    """Create a sample contract."""
    return UnifiedContract(
        source="kalshi",
        market_id="test-market",
        contract_id="test-contract",
        name="YES",
        side="YES",
        outcome_type="binary",
        price_bid=0.5,
        price_ask=0.55,
    )


@pytest.fixture
def sample_market(sample_contract):
    """Create a sample market."""
    return UnifiedMarket(
        source="kalshi",
        market_id="test-market",
        name="Will Bitcoin reach $100k?",
        category="Crypto",
        contracts=[sample_contract],
    )


@pytest.fixture
def matcher():
    """Create a market matcher instance."""
    return MarketMatcher()


class TestMarketMatcher:
    """Tests for MarketMatcher class."""
    
    def test_initialization_default(self):
        """Test default initialization."""
        matcher = MarketMatcher()
        assert matcher.name_weight == 0.4
        assert matcher.category_weight == 0.2
        assert matcher.contract_weight == 0.3
        assert matcher.temporal_weight == 0.1
        assert matcher.min_score_threshold == 0.5
    
    def test_initialization_custom_weights(self):
        """Test custom weight initialization."""
        matcher = MarketMatcher(
            name_weight=0.5,
            category_weight=0.2,
            contract_weight=0.2,
            temporal_weight=0.1,
        )
        assert matcher.name_weight == 0.5
    
    def test_initialization_invalid_weights(self):
        """Test that invalid weights raise error."""
        with pytest.raises(ValueError):
            MarketMatcher(
                name_weight=0.5,
                category_weight=0.3,
                contract_weight=0.3,
                temporal_weight=0.1,  # Sum > 1.0
            )
    
    def test_clean_text(self, matcher):
        """Test text cleaning."""
        assert matcher._clean_text("Hello, World!") == "hello world"
        assert matcher._clean_text("Test  Multiple   Spaces") == "test multiple spaces"
        assert matcher._clean_text("UPPERCASE") == "uppercase"
    
    def test_fuzzy_match_identical(self, matcher):
        """Test fuzzy matching with identical strings."""
        score = matcher._fuzzy_match("Bitcoin", "Bitcoin")
        assert score == 1.0
    
    def test_fuzzy_match_similar(self, matcher):
        """Test fuzzy matching with similar strings."""
        score = matcher._fuzzy_match("Bitcoin", "Bitcoins")
        assert 0.8 < score < 1.0
    
    def test_fuzzy_match_dissimilar(self, matcher):
        """Test fuzzy matching with dissimilar strings."""
        score = matcher._fuzzy_match("Apple", "Orange")
        assert score < 0.5
    
    def test_category_similarity_exact_match(self, matcher):
        """Test category similarity with exact match."""
        market_a = UnifiedMarket(
            source="kalshi",
            market_id="1",
            name="Market A",
            category="Politics",
        )
        market_b = UnifiedMarket(
            source="polymarket",
            market_id="2",
            name="Market B",
            category="Politics",
        )
        
        score = matcher._compute_category_similarity(market_a, market_b)
        assert score == 1.0
    
    def test_category_similarity_partial_match(self, matcher):
        """Test category similarity with partial match."""
        market_a = UnifiedMarket(
            source="kalshi",
            market_id="1",
            name="Market A",
            category="Politics",
        )
        market_b = UnifiedMarket(
            source="polymarket",
            market_id="2",
            name="Market B",
            category="U.S. Politics",
        )
        
        score = matcher._compute_category_similarity(market_a, market_b)
        assert score == 0.7
    
    def test_category_similarity_no_match(self, matcher):
        """Test category similarity with no match."""
        market_a = UnifiedMarket(
            source="kalshi",
            market_id="1",
            name="Market A",
            category="Politics",
        )
        market_b = UnifiedMarket(
            source="polymarket",
            market_id="2",
            name="Market B",
            category="Sports",
        )
        
        score = matcher._compute_category_similarity(market_a, market_b)
        assert score == 0.0
    
    def test_category_similarity_missing(self, matcher):
        """Test category similarity with missing category."""
        market_a = UnifiedMarket(
            source="kalshi",
            market_id="1",
            name="Market A",
            category="Politics",
        )
        market_b = UnifiedMarket(
            source="polymarket",
            market_id="2",
            name="Market B",
            category=None,
        )
        
        score = matcher._compute_category_similarity(market_a, market_b)
        assert score == 0.5
    
    def test_contract_similarity_binary(self, matcher):
        """Test contract similarity with binary outcomes."""
        contract_yes = UnifiedContract(
            source="kalshi",
            market_id="1",
            contract_id="yes",
            name="YES",
            side="YES",
            outcome_type="binary",
        )
        contract_no = UnifiedContract(
            source="kalshi",
            market_id="1",
            contract_id="no",
            name="NO",
            side="NO",
            outcome_type="binary",
        )
        
        market_a = UnifiedMarket(
            source="kalshi",
            market_id="1",
            name="Market A",
            contracts=[contract_yes, contract_no],
        )
        market_b = UnifiedMarket(
            source="polymarket",
            market_id="2",
            name="Market B",
            contracts=[contract_yes, contract_no],
        )
        
        score = matcher._compute_contract_similarity(market_a, market_b)
        assert score == 1.0
    
    def test_find_matches_empty_lists(self, matcher):
        """Test find_matches with empty lists."""
        matches = matcher.find_matches([], [])
        assert matches == []
    
    def test_find_matches_identical_markets(self, matcher, sample_market):
        """Test finding matches with identical markets from different sources."""
        market_a = UnifiedMarket(
            source="kalshi",
            market_id="1",
            name="Will Bitcoin reach $100k?",
            category="Crypto",
            contracts=[
                UnifiedContract(
                    source="kalshi",
                    market_id="1",
                    contract_id="yes",
                    name="YES",
                    side="YES",
                    outcome_type="binary",
                )
            ],
        )
        market_b = UnifiedMarket(
            source="polymarket",
            market_id="2",
            name="Will Bitcoin reach $100k?",
            category="Crypto",
            contracts=[
                UnifiedContract(
                    source="polymarket",
                    market_id="2",
                    contract_id="yes",
                    name="YES",
                    side="YES",
                    outcome_type="binary",
                )
            ],
        )
        
        matches = matcher.find_matches([market_a], [market_b])
        assert len(matches) >= 1
        assert matches[0].match_score > 0.8
    
    def test_find_matches_different_sources_only(self, matcher):
        """Test that cross_source_only filter works."""
        market = UnifiedMarket(
            source="kalshi",
            market_id="1",
            name="Market A",
        )
        
        matches = matcher.find_matches(
            [market], [market], cross_source_only=True
        )
        assert len(matches) == 0
    
    def test_match_result_representation(self, sample_market):
        """Test MatchResult string representation."""
        market_a = UnifiedMarket(
            source="kalshi",
            market_id="1",
            name="Market A",
        )
        market_b = UnifiedMarket(
            source="polymarket",
            market_id="2",
            name="Market B",
        )
        
        result = MatchResult(
            market_a=market_a,
            market_b=market_b,
            match_score=0.85,
            name_similarity=0.8,
            category_similarity=1.0,
            contract_similarity=0.7,
            temporal_proximity=0.9,
            confidence="high",
        )
        
        repr_str = repr(result)
        assert "kalshi/1" in repr_str
        assert "polymarket/2" in repr_str
        assert "0.85" in repr_str
        assert "high" in repr_str
    
    def test_compute_confidence_high(self, matcher):
        """Test high confidence computation."""
        confidence = matcher._compute_confidence(
            overall_score=0.85,
            name_sim=0.8,
            matching_contract_count=2,
            total_contracts=2,
        )
        assert confidence == "high"
    
    def test_compute_confidence_medium(self, matcher):
        """Test medium confidence computation."""
        confidence = matcher._compute_confidence(
            overall_score=0.7,
            name_sim=0.6,
            matching_contract_count=1,
            total_contracts=2,
        )
        assert confidence == "medium"
    
    def test_compute_confidence_low(self, matcher):
        """Test low confidence computation."""
        confidence = matcher._compute_confidence(
            overall_score=0.4,
            name_sim=0.3,
            matching_contract_count=0,
            total_contracts=2,
        )
        assert confidence == "low"
    
    def test_match_single_pair(self, matcher):
        """Test matching a single pair of markets."""
        market_a = UnifiedMarket(
            source="kalshi",
            market_id="1",
            name="Bitcoin price",
        )
        market_b = UnifiedMarket(
            source="polymarket",
            market_id="2",
            name="Bitcoin price",
        )
        
        result = matcher.match_single_pair(market_a, market_b)
        assert isinstance(result, MatchResult)
        assert result.market_a == market_a
        assert result.market_b == market_b
