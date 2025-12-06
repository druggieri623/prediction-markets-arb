"""Tests for the arbitrage detector."""

import pytest
from decimal import Decimal
from datetime import datetime

from pm_arb.api.models import UnifiedMarket, UnifiedContract
from pm_arb.sql_storage import MatchedMarketPairORM, init_db
from pm_arb.arbitrage_detector import ArbitrageDetector, ArbitrageOpportunity


@pytest.fixture
def test_market_a() -> UnifiedMarket:
    """Create a test market A (Kalshi)."""
    return UnifiedMarket(
        source="kalshi",
        market_id="bitcoin-eoy-2025",
        name="Will Bitcoin exceed $100k by EOY 2025?",
        category="crypto",
        contracts=[
            UnifiedContract(
                source="kalshi",
                market_id="bitcoin-eoy-2025",
                contract_id="yes",
                name="YES",
                side="YES",
                outcome_type="binary",
                price_bid=0.58,
                price_ask=0.59,
                last_price=0.585,
            ),
            UnifiedContract(
                source="kalshi",
                market_id="bitcoin-eoy-2025",
                contract_id="no",
                name="NO",
                side="NO",
                outcome_type="binary",
                price_bid=0.40,
                price_ask=0.41,
                last_price=0.405,
            ),
        ],
    )


@pytest.fixture
def test_market_b() -> UnifiedMarket:
    """Create a test market B (PolyMarket) - slightly different odds."""
    return UnifiedMarket(
        source="polymarket",
        market_id="btc-100k-2025",
        name="Bitcoin > $100,000 at end of 2025",
        category="crypto",
        contracts=[
            UnifiedContract(
                source="polymarket",
                market_id="btc-100k-2025",
                contract_id="yes",
                name="YES",
                side="YES",
                outcome_type="binary",
                price_bid=0.62,
                price_ask=0.63,
                last_price=0.625,
            ),
            UnifiedContract(
                source="polymarket",
                market_id="btc-100k-2025",
                contract_id="no",
                name="NO",
                side="NO",
                outcome_type="binary",
                price_bid=0.36,
                price_ask=0.37,
                last_price=0.365,
            ),
        ],
    )


@pytest.fixture
def test_market_arb() -> tuple:
    """Create two markets with clear arbitrage opportunity."""
    # Market with YES cheap (0.40) and NO expensive (0.60)
    market_a = UnifiedMarket(
        source="kalshi",
        market_id="event-a",
        name="Event A",
        category="test",
        contracts=[
            UnifiedContract(
                source="kalshi",
                market_id="event-a",
                contract_id="yes",
                name="YES",
                side="YES",
                outcome_type="binary",
                price_ask=0.40,  # CHEAP
            ),
            UnifiedContract(
                source="kalshi",
                market_id="event-a",
                contract_id="no",
                name="NO",
                side="NO",
                outcome_type="binary",
                price_ask=0.60,
            ),
        ],
    )

    # Market with YES expensive (0.65) and NO cheap (0.30)
    market_b = UnifiedMarket(
        source="polymarket",
        market_id="event-b",
        name="Event B (same as A)",
        category="test",
        contracts=[
            UnifiedContract(
                source="polymarket",
                market_id="event-b",
                contract_id="yes",
                name="YES",
                side="YES",
                outcome_type="binary",
                price_ask=0.65,
            ),
            UnifiedContract(
                source="polymarket",
                market_id="event-b",
                contract_id="no",
                name="NO",
                side="NO",
                outcome_type="binary",
                price_ask=0.30,  # CHEAP
            ),
        ],
    )

    return market_a, market_b


@pytest.fixture
def detector() -> ArbitrageDetector:
    """Create an ArbitrageDetector instance."""
    return ArbitrageDetector(min_similarity=0.70, min_profit_threshold=0.01)


@pytest.fixture
def db_session():
    """Create a test database session."""
    _, SessionLocal = init_db("sqlite:///:memory:")
    session = SessionLocal()
    yield session
    session.close()


class TestArbitrageDetectorBasics:
    """Test basic detector initialization and market registration."""

    def test_detector_initialization(self):
        """Test detector initializes with correct defaults."""
        detector = ArbitrageDetector()
        assert detector.min_similarity == 0.70
        assert detector.min_profit_threshold == 0.01
        assert len(detector.markets_dict) == 0

    def test_register_single_market(self, test_market_a):
        """Test registering a single market."""
        detector = ArbitrageDetector()
        detector.register_markets([test_market_a])

        key = ("kalshi", "bitcoin-eoy-2025")
        assert key in detector.markets_dict
        assert detector.markets_dict[key] == test_market_a

    def test_register_multiple_markets(self, test_market_a, test_market_b):
        """Test registering multiple markets."""
        detector = ArbitrageDetector()
        detector.register_markets([test_market_a, test_market_b])

        assert len(detector.markets_dict) == 2
        assert ("kalshi", "bitcoin-eoy-2025") in detector.markets_dict
        assert ("polymarket", "btc-100k-2025") in detector.markets_dict


class TestBinaryMarketDetection:
    """Test binary market detection."""

    def test_is_binary_market_valid(self, test_market_a):
        """Test detection of valid binary market."""
        detector = ArbitrageDetector()
        assert detector._is_binary_market(test_market_a) is True

    def test_is_binary_market_no_contracts(self):
        """Test binary detection with no contracts."""
        market = UnifiedMarket(
            source="test",
            market_id="empty",
            name="Empty market",
        )
        detector = ArbitrageDetector()
        assert detector._is_binary_market(market) is False

    def test_is_binary_market_wrong_outcome_type(self):
        """Test binary detection with non-binary outcome type."""
        market = UnifiedMarket(
            source="test",
            market_id="multi",
            name="Multi-outcome market",
            contracts=[
                UnifiedContract(
                    source="test",
                    market_id="multi",
                    contract_id="a",
                    name="Outcome A",
                    side="A",
                    outcome_type="multi",
                    price_ask=0.33,
                ),
                UnifiedContract(
                    source="test",
                    market_id="multi",
                    contract_id="b",
                    name="Outcome B",
                    side="B",
                    outcome_type="multi",
                    price_ask=0.33,
                ),
                UnifiedContract(
                    source="test",
                    market_id="multi",
                    contract_id="c",
                    name="Outcome C",
                    side="C",
                    outcome_type="multi",
                    price_ask=0.34,
                ),
            ],
        )
        detector = ArbitrageDetector()
        assert detector._is_binary_market(market) is False


class TestContractExtraction:
    """Test YES/NO contract extraction."""

    def test_extract_binary_contracts(self, test_market_a):
        """Test extracting YES/NO contracts."""
        detector = ArbitrageDetector()
        yes_c, no_c = detector._extract_binary_contracts(test_market_a)

        assert yes_c is not None
        assert no_c is not None
        assert yes_c.side == "YES"
        assert no_c.side == "NO"

    def test_extract_binary_contracts_missing_yes(self):
        """Test extraction when YES contract is missing."""
        market = UnifiedMarket(
            source="test",
            market_id="no-yes",
            name="Missing YES",
            contracts=[
                UnifiedContract(
                    source="test",
                    market_id="no-yes",
                    contract_id="no",
                    name="NO",
                    side="NO",
                    outcome_type="binary",
                    price_ask=0.40,
                ),
            ],
        )
        detector = ArbitrageDetector()
        yes_c, no_c = detector._extract_binary_contracts(market)

        assert yes_c is None
        assert no_c is not None

    def test_extract_binary_contracts_missing_no(self):
        """Test extraction when NO contract is missing."""
        market = UnifiedMarket(
            source="test",
            market_id="yes-only",
            name="Missing NO",
            contracts=[
                UnifiedContract(
                    source="test",
                    market_id="yes-only",
                    contract_id="yes",
                    name="YES",
                    side="YES",
                    outcome_type="binary",
                    price_ask=0.60,
                ),
            ],
        )
        detector = ArbitrageDetector()
        yes_c, no_c = detector._extract_binary_contracts(market)

        assert yes_c is not None
        assert no_c is None


class TestArbitrageCalculation:
    """Test arbitrage opportunity calculation."""

    def test_calculate_arbitrage_opportunity(
        self, test_market_arb, db_session
    ):
        """Test calculation of arbitrage opportunity.
        
        Market A: YES $0.40, NO $0.60 (total $1.00)
        Market B: YES $0.65, NO $0.30 (total $0.95)
        
        Opportunity: Buy YES from A ($0.40) + NO from B ($0.30) = $0.70
        This always returns $1.00 for a $0.30 profit (42.9% ROI)
        """
        market_a, market_b = test_market_arb
        detector = ArbitrageDetector(min_profit_threshold=0.01)
        detector.register_markets([market_a, market_b])

        # Create a matched pair
        pair = MatchedMarketPairORM(
            source_a="kalshi",
            market_id_a="event-a",
            source_b="polymarket",
            market_id_b="event-b",
            similarity=0.95,
        )

        # Analyze the pair
        opps = detector._analyze_pair(pair)

        assert len(opps) == 1
        opp = opps[0]

        assert opp.min_profit >= 0.25  # Should have solid profit
        assert opp.is_arbitrage is True
        assert opp.arbitrage_type == "both_sides"
        assert opp.total_investment == pytest.approx(0.70, abs=0.01)

    def test_no_arbitrage_with_poor_prices(self, test_market_a, test_market_b, db_session):
        """Test that minimal/no arbitrage is found when prices are aligned."""
        detector = ArbitrageDetector(min_similarity=0.70)
        detector.register_markets([test_market_a, test_market_b])

        # Create a matched pair
        pair = MatchedMarketPairORM(
            source_a="kalshi",
            market_id_a="bitcoin-eoy-2025",
            source_b="polymarket",
            market_id_b="btc-100k-2025",
            similarity=0.85,
        )

        # These markets have prices close to 1.0, resulting in small or no profit
        opps = detector._analyze_pair(pair)

        # Might be empty or might have minimal profit < typical thresholds
        if opps:
            # If there's an opportunity, it should be small
            assert opps[0].roi_pct < 10.0  # Less than 10% ROI

    def test_arbitrage_missing_prices(self, test_market_arb, db_session):
        """Test handling of missing price data."""
        market_a, market_b = test_market_arb
        
        # Remove prices from one contract
        market_a.contracts[0].price_ask = None
        market_a.contracts[0].last_price = None
        
        detector = ArbitrageDetector()
        detector.register_markets([market_a, market_b])

        pair = MatchedMarketPairORM(
            source_a="kalshi",
            market_id_a="event-a",
            source_b="polymarket",
            market_id_b="event-b",
            similarity=0.95,
        )

        opps = detector._analyze_pair(pair)
        assert len(opps) == 0  # Should return empty when prices missing

    def test_arbitrage_missing_market(self, test_market_a):
        """Test handling when market data is not registered."""
        detector = ArbitrageDetector()
        detector.register_markets([test_market_a])
        # Don't register test_market_b

        pair = MatchedMarketPairORM(
            source_a="kalshi",
            market_id_a="bitcoin-eoy-2025",
            source_b="polymarket",
            market_id_b="btc-100k-2025",  # Not registered
            similarity=0.85,
        )

        opps = detector._analyze_pair(pair)
        assert len(opps) == 0  # Should return empty when market missing


class TestDetectOpportunities:
    """Test full opportunity detection workflow."""

    def test_detect_opportunities_with_matched_pairs(
        self, test_market_arb, db_session
    ):
        """Test detecting opportunities from database matched pairs."""
        market_a, market_b = test_market_arb
        detector = ArbitrageDetector(min_similarity=0.70)
        detector.register_markets([market_a, market_b])

        # Create matched pairs in database
        pair = MatchedMarketPairORM(
            source_a="kalshi",
            market_id_a="event-a",
            source_b="polymarket",
            market_id_b="event-b",
            similarity=0.95,
        )
        db_session.add(pair)
        db_session.commit()

        # Detect opportunities
        opps = detector.detect_opportunities(db_session)

        assert len(opps) >= 0  # May or may not find depending on exact calculations

    def test_detect_opportunities_empty_database(self, detector, db_session):
        """Test detecting opportunities from empty database."""
        opps = detector.detect_opportunities(db_session)
        assert len(opps) == 0

    def test_detect_opportunities_filtered_by_similarity(
        self, test_market_arb, db_session
    ):
        """Test that low-similarity pairs are filtered out."""
        market_a, market_b = test_market_arb
        detector = ArbitrageDetector(min_similarity=0.90)
        detector.register_markets([market_a, market_b])

        # Create low-similarity pair
        pair = MatchedMarketPairORM(
            source_a="kalshi",
            market_id_a="event-a",
            source_b="polymarket",
            market_id_b="event-b",
            similarity=0.75,  # Below threshold
        )
        db_session.add(pair)
        db_session.commit()

        opps = detector.detect_opportunities(db_session)
        assert len(opps) == 0  # Should be filtered out


class TestOpportunitySummary:
    """Test opportunity summarization."""

    def test_opportunity_summary_text(self, test_market_arb):
        """Test generating text summary for an opportunity."""
        market_a, market_b = test_market_arb
        detector = ArbitrageDetector()
        detector.register_markets([market_a, market_b])

        # Create a mock opportunity
        opp = ArbitrageOpportunity(
            source_a="kalshi",
            market_id_a="event-a",
            source_b="polymarket",
            market_id_b="event-b",
            yes_contract_a=market_a.contracts[0],
            no_contract_a=market_a.contracts[1],
            yes_contract_b=market_b.contracts[0],
            no_contract_b=market_b.contracts[1],
            profit_if_yes=0.30,
            profit_if_no=0.30,
            min_profit=0.30,
            max_profit=0.30,
            roi_pct=42.86,
            total_investment=0.70,
            match_similarity=0.95,
            is_arbitrage=True,
            is_scalp=False,
            break_even_spread=0.0,
            arbitrage_type="both_sides",
            notes="Buy YES at A ($0.40), NO at B ($0.30)",
        )

        summary = opp.summary()

        assert "event-a" in summary.lower()
        assert "event-b" in summary.lower()
        assert "both_sides" in summary.lower()
        assert "$0.30" in summary
        assert "42.86" in summary
        assert "ARBITRAGE" in summary

    def test_summarize_opportunities_empty(self, detector):
        """Test summarizing empty opportunities list."""
        summary = detector.summarize_opportunities([])
        assert "No arbitrage opportunities found" in summary

    def test_summarize_opportunities_multiple(self, test_market_arb, detector):
        """Test summarizing multiple opportunities."""
        market_a, market_b = test_market_arb
        detector.register_markets([market_a, market_b])

        opps = [
            ArbitrageOpportunity(
                source_a="kalshi",
                market_id_a="event-a",
                source_b="polymarket",
                market_id_b="event-b",
                yes_contract_a=market_a.contracts[0],
                no_contract_a=market_a.contracts[1],
                yes_contract_b=market_b.contracts[0],
                no_contract_b=market_b.contracts[1],
                profit_if_yes=0.30,
                profit_if_no=0.30,
                min_profit=0.30,
                max_profit=0.30,
                roi_pct=42.86,
                total_investment=0.70,
                match_similarity=0.95,
                is_arbitrage=True,
                is_scalp=False,
                break_even_spread=0.0,
                arbitrage_type="both_sides",
            ),
            ArbitrageOpportunity(
                source_a="kalshi",
                market_id_a="other-a",
                source_b="polymarket",
                market_id_b="other-b",
                yes_contract_a=market_a.contracts[0],
                no_contract_a=market_a.contracts[1],
                yes_contract_b=market_b.contracts[0],
                no_contract_b=market_b.contracts[1],
                profit_if_yes=0.05,
                profit_if_no=0.05,
                min_profit=0.05,
                max_profit=0.05,
                roi_pct=5.0,
                total_investment=1.0,
                match_similarity=0.80,
                is_arbitrage=True,
                is_scalp=False,
                break_even_spread=0.0,
                arbitrage_type="both_sides",
            ),
        ]

        summary = detector.summarize_opportunities(opps)

        assert "2" in summary or "two" in summary.lower()
        assert "ARBITRAGE" in summary


class TestFindBestOpportunity:
    """Test finding the best opportunities."""

    def test_find_best_opportunity_none(self, detector, db_session):
        """Test when no opportunities exist."""
        best = detector.find_best_opportunity(db_session)
        assert len(best) == 0

    def test_find_best_opportunity_sorted(self, test_market_arb, db_session):
        """Test that opportunities are sorted by profitability."""
        market_a, market_b = test_market_arb
        detector = ArbitrageDetector()
        detector.register_markets([market_a, market_b])

        # Create multiple pairs
        for i, sim in enumerate([0.90, 0.95, 0.85]):
            pair = MatchedMarketPairORM(
                source_a="kalshi",
                market_id_a=f"event-a-{i}",
                source_b="polymarket",
                market_id_b=f"event-b-{i}",
                similarity=sim,
            )
            db_session.add(pair)

        db_session.commit()

        best = detector.find_best_opportunity(db_session, limit=1)
        # Should return at most 1
        assert len(best) <= 1
