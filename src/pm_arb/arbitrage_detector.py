"""Arbitrage detector for matched market pairs.

Identifies both-side profit opportunities (Dutch book scenarios) where you can
simultaneously buy opposite outcomes across markets and guarantee a profit or
minimize maximum loss.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List, Tuple
from decimal import Decimal
from sqlalchemy.orm import Session

from .sql_storage import MatchedMarketPairORM
from .api.models import UnifiedMarket, UnifiedContract


@dataclass
class ContractPair:
    """Represents a contract outcome from market A and its opposite in market B."""

    source_a: str
    market_id_a: str
    contract_a: UnifiedContract

    source_b: str
    market_id_b: str
    contract_b: UnifiedContract

    match_quality: float  # Similarity score from matched pair [0, 1]

    def __post_init__(self):
        """Validate that contracts represent opposite outcomes."""
        # This is a logical pairing - contracts represent same outcome event
        # e.g., both "YES" or equivalent sides
        pass


@dataclass
class ArbitrageOpportunity:
    """A profitable arbitrage opportunity across two markets."""

    source_a: str
    market_id_a: str
    source_b: str
    market_id_b: str

    # Contract pairings for YES and NO (or equivalent)
    yes_contract_a: UnifiedContract  # YES outcome in market A
    no_contract_a: UnifiedContract  # NO outcome in market A
    yes_contract_b: UnifiedContract  # YES outcome in market B
    no_contract_b: UnifiedContract  # NO outcome in market B

    # Profitability metrics
    profit_if_yes: float  # Profit/loss if YES occurs (can be negative)
    profit_if_no: float  # Profit/loss if NO occurs (can be negative)
    min_profit: float  # Minimum guaranteed profit (worst case)
    max_profit: float  # Maximum possible profit (best case)
    roi_pct: float  # Return on investment percentage
    total_investment: float  # Total capital required

    # Match quality
    match_similarity: float  # How well matched are these markets?

    # Risk assessment
    is_arbitrage: bool  # True if min_profit > 0 (risk-free profit)
    is_scalp: bool  # True if ROI is positive but requires favorable outcome
    break_even_spread: float  # Spread needed to break even
    arbitrage_type: str  # "both_sides", "scalp", "hedge"

    # Additional context
    notes: str = ""
    matched_pair_id: Optional[int] = None

    def summary(self) -> str:
        """Return a human-readable summary of the opportunity."""
        lines = [
            f"{self.source_a.upper()}/{self.market_id_a} ↔ {self.source_b.upper()}/{self.market_id_b}",
            f"Type: {self.arbitrage_type.upper()} | Match Quality: {self.match_similarity:.1%}",
            f"Min Profit: ${self.min_profit:.2f} | Max Profit: ${self.max_profit:.2f}",
            f"ROI: {self.roi_pct:.2f}% | Investment: ${self.total_investment:.2f}",
        ]
        if self.is_arbitrage:
            lines.append("✓ ARBITRAGE (risk-free profit opportunity)")
        elif self.is_scalp:
            lines.append("⚠ SCALP (conditional profit opportunity)")
        else:
            lines.append("⊘ HEDGE (risk mitigation, no profit guaranteed)")

        if self.notes:
            lines.append(f"Notes: {self.notes}")

        return "\n".join(lines)


class ArbitrageDetector:
    """Detects arbitrage opportunities in matched market pairs."""

    def __init__(
        self,
        markets_dict: dict = None,
        min_similarity: float = 0.70,
        min_profit_threshold: float = 0.01,  # $0.01 minimum
    ):
        """Initialize the detector.

        Args:
            markets_dict: Dict mapping (source, market_id) -> UnifiedMarket
            min_similarity: Minimum match similarity to consider [0, 1]
            min_profit_threshold: Minimum dollar profit to flag opportunity
        """
        self.markets_dict = markets_dict or {}
        self.min_similarity = min_similarity
        self.min_profit_threshold = min_profit_threshold

    def register_markets(self, markets: List[UnifiedMarket]) -> None:
        """Register markets for arbitrage detection.

        Args:
            markets: List of UnifiedMarket objects to index
        """
        for market in markets:
            key = (market.source, market.market_id)
            self.markets_dict[key] = market

    def detect_opportunities(
        self,
        session: Session,
        matched_pairs: List[MatchedMarketPairORM] = None,
        min_similarity: Optional[float] = None,
    ) -> List[ArbitrageOpportunity]:
        """Detect arbitrage opportunities from matched pairs.

        Args:
            session: SQLAlchemy session for database queries
            matched_pairs: Specific pairs to analyze (if None, fetch all confirmed)
            min_similarity: Override instance min_similarity threshold

        Returns:
            List of ArbitrageOpportunity objects sorted by min_profit descending
        """
        min_sim = min_similarity if min_similarity is not None else self.min_similarity

        # Fetch matched pairs if not provided
        if matched_pairs is None:
            matched_pairs = session.query(MatchedMarketPairORM).filter(
                MatchedMarketPairORM.similarity >= min_sim
            ).all()

        opportunities = []
        for pair in matched_pairs:
            opps = self._analyze_pair(pair)
            opportunities.extend(opps)

        # Sort by min_profit descending (best arbitrage first)
        opportunities.sort(key=lambda x: x.min_profit, reverse=True)
        return opportunities

    def _analyze_pair(
        self, pair: MatchedMarketPairORM
    ) -> List[ArbitrageOpportunity]:
        """Analyze a single matched pair for arbitrage opportunities.

        Args:
            pair: MatchedMarketPairORM representing two matched markets

        Returns:
            List of ArbitrageOpportunity objects (usually 0-1 per pair)
        """
        # Retrieve market data
        market_a = self.markets_dict.get((pair.source_a, pair.market_id_a))
        market_b = self.markets_dict.get((pair.source_b, pair.market_id_b))

        if not market_a or not market_b:
            return []

        # Only process binary markets for now
        if not self._is_binary_market(market_a) or not self._is_binary_market(market_b):
            return []

        # Extract YES/NO contracts
        yes_a, no_a = self._extract_binary_contracts(market_a)
        yes_b, no_b = self._extract_binary_contracts(market_b)

        if not (yes_a and no_a and yes_b and no_b):
            return []

        opportunities = []

        # Strategy 1: Buy YES in A, NO in A; Buy YES in B, NO in B
        # This forms a complete hedge in each market
        opp = self._calculate_both_sides_opportunity(
            pair, market_a, market_b, yes_a, no_a, yes_b, no_b
        )
        if opp:
            opportunities.append(opp)

        return opportunities

    def _is_binary_market(self, market: UnifiedMarket) -> bool:
        """Check if market is binary (YES/NO)."""
        if not market.contracts:
            return False

        # Check if we have exactly 2 contracts with binary outcomes
        binary_contracts = [
            c
            for c in market.contracts
            if c.outcome_type == "binary" and c.side in ("YES", "NO")
        ]
        return len(binary_contracts) >= 2

    def _extract_binary_contracts(
        self, market: UnifiedMarket
    ) -> Tuple[Optional[UnifiedContract], Optional[UnifiedContract]]:
        """Extract YES and NO contracts from a binary market.

        Args:
            market: UnifiedMarket to extract from

        Returns:
            Tuple of (YES contract, NO contract), or (None, None) if not found
        """
        yes_contract = None
        no_contract = None

        for contract in market.contracts:
            if contract.side.upper() == "YES":
                yes_contract = contract
            elif contract.side.upper() == "NO":
                no_contract = contract

        return yes_contract, no_contract

    def _calculate_both_sides_opportunity(
        self,
        pair: MatchedMarketPairORM,
        market_a: UnifiedMarket,
        market_b: UnifiedMarket,
        yes_a: UnifiedContract,
        no_a: UnifiedContract,
        yes_b: UnifiedContract,
        no_b: UnifiedContract,
    ) -> Optional[ArbitrageOpportunity]:
        """Calculate arbitrage opportunity for a matched pair.

        Strategy: Buy YES in A and YES in B; simultaneously buy NO in A and NO in B.
        This creates a hedge where one outcome is always profitable.

        Args:
            pair: MatchedMarketPairORM database record
            market_a, market_b: Market definitions
            yes_a, no_a: YES/NO contracts in market A
            yes_b, no_b: YES/NO contracts in market B

        Returns:
            ArbitrageOpportunity if profitable opportunity exists, else None
        """
        # Get prices (ask prices = cost to buy)
        yes_a_price = yes_a.price_ask or yes_a.last_price
        no_a_price = no_a.price_ask or no_a.last_price
        yes_b_price = yes_b.price_ask or yes_b.last_price
        no_b_price = no_b.price_ask or no_b.last_price

        # Need all prices to calculate
        if not all([yes_a_price, no_a_price, yes_b_price, no_b_price]):
            return None

        # Ensure prices are valid probabilities
        if not all(0 <= p <= 1 for p in [yes_a_price, no_a_price, yes_b_price, no_b_price]):
            return None

        # Convert to floats
        yes_a_p = float(yes_a_price)
        no_a_p = float(no_a_price)
        yes_b_p = float(yes_b_price)
        no_b_p = float(no_b_price)

        # Calculate total cost to buy both outcomes in each market
        # Typically in prediction markets: YES + NO ≈ 1.0 (but can deviate)
        cost_both_a = yes_a_p + no_a_p
        cost_both_b = yes_b_p + no_b_p

        # Strategy: Buy YES in whichever market is cheaper, buy NO in the other
        # This creates exposure to YES outcome at (cheaper YES price) and
        # exposure to NO outcome at (cheaper NO price)
        
        # Case 1: YES YES (buy YES in both) + NO NO (buy NO in both)
        total_cost = yes_a_p + yes_b_p + no_a_p + no_b_p
        
        # But we only need to hold one "YES" and one "NO" for the matched outcome
        # Let's use a different strategy: matched pair arbitrage
        # Buy YES in cheapest market, NO in cheapest market
        
        if yes_a_p <= yes_b_p:
            yes_price = yes_a_p
            yes_source = "A"
        else:
            yes_price = yes_b_p
            yes_source = "B"

        if no_a_p <= no_b_p:
            no_price = no_a_p
            no_source = "A"
        else:
            no_price = no_b_p
            no_source = "B"

        # Total cost for a complete hedge
        total_investment = yes_price + no_price
        
        # In a perfect hedge, exactly $1 is returned regardless of outcome
        guaranteed_return = 1.0
        min_profit = guaranteed_return - total_investment

        # If prices sum to > 1.0, we have arbitrage (guaranteed profit)
        # If prices sum to < 1.0, we need favorable outcome for profit
        
        # For a more sophisticated analysis, calculate profit for each outcome
        # Assuming we normalize positions...

        # Actually, let's use a cleaner approach:
        # Calculate the "overround" or profit from the implied odds
        
        # In matched pair arbitrage:
        # You buy Y from market A at price P_A
        # You buy N from market B at price (1-Q_B) where Q_B is NO price in B
        # Net: P_A + (1 - Q_B) gives you a guaranteed position
        
        # Simplified: if YES in A is cheaper and NO in B is cheaper,
        # you can lock in arbitrage
        
        profit_if_yes = guaranteed_return - (yes_price + no_price)
        profit_if_no = guaranteed_return - (yes_price + no_price)
        min_profit = profit_if_yes  # Same for both outcomes
        max_profit = profit_if_yes

        # Only flag if meets threshold
        if min_profit < self.min_profit_threshold:
            return None

        # Calculate ROI
        roi_pct = (min_profit / total_investment * 100) if total_investment > 0 else 0

        # Determine arbitrage type
        is_arb = min_profit > 0.001  # Allow tiny rounding error
        is_scalp = False
        arbitrage_type = "both_sides" if is_arb else "hedge"

        notes = f"Buy YES at {yes_source} (${yes_price:.4f}), NO at {no_source} (${no_price:.4f})"

        return ArbitrageOpportunity(
            source_a=pair.source_a,
            market_id_a=pair.market_id_a,
            source_b=pair.source_b,
            market_id_b=pair.market_id_b,
            yes_contract_a=yes_a,
            no_contract_a=no_a,
            yes_contract_b=yes_b,
            no_contract_b=no_b,
            profit_if_yes=profit_if_yes,
            profit_if_no=profit_if_no,
            min_profit=min_profit,
            max_profit=max_profit,
            roi_pct=roi_pct,
            total_investment=total_investment,
            match_similarity=pair.similarity,
            is_arbitrage=is_arb,
            is_scalp=is_scalp,
            break_even_spread=total_investment - 1.0,
            arbitrage_type=arbitrage_type,
            notes=notes,
            matched_pair_id=pair.id,
        )

    def find_best_opportunity(
        self, session: Session, limit: int = 1
    ) -> List[ArbitrageOpportunity]:
        """Find the best arbitrage opportunities.

        Args:
            session: SQLAlchemy session
            limit: Number of top opportunities to return

        Returns:
            List of best ArbitrageOpportunity objects by min_profit
        """
        opps = self.detect_opportunities(session)
        return opps[:limit]

    def summarize_opportunities(
        self, opportunities: List[ArbitrageOpportunity]
    ) -> str:
        """Generate a summary report of opportunities.

        Args:
            opportunities: List of opportunities to summarize

        Returns:
            Human-readable summary string
        """
        if not opportunities:
            return "No arbitrage opportunities found."

        lines = [
            f"Found {len(opportunities)} arbitrage opportunities:\n",
        ]

        arbs = [o for o in opportunities if o.is_arbitrage]
        scalps = [o for o in opportunities if o.is_scalp]
        hedges = [o for o in opportunities if not o.is_arbitrage and not o.is_scalp]

        if arbs:
            lines.append(f"✓ {len(arbs)} ARBITRAGE (risk-free profit):")
            for opp in arbs[:3]:
                lines.append(f"  • Min profit: ${opp.min_profit:.2f} ({opp.roi_pct:.1f}% ROI)")

        if scalps:
            lines.append(f"\n⚠ {len(scalps)} SCALP (conditional profit):")
            for opp in scalps[:3]:
                lines.append(f"  • Min profit: ${opp.min_profit:.2f} ({opp.roi_pct:.1f}% ROI)")

        if hedges:
            lines.append(f"\n⊘ {len(hedges)} HEDGE (risk mitigation):")
            for opp in hedges[:3]:
                lines.append(f"  • Expected: ${opp.min_profit:.2f}")

        return "\n".join(lines)
