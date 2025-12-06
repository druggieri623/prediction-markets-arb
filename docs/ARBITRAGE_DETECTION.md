"""Documentation for Arbitrage Detection System"""

# Arbitrage Detection System

## Overview

The arbitrage detector identifies **both-side profit opportunities** across matched prediction markets. It analyzes matched market pairs to find scenarios where you can simultaneously buy opposite outcomes across platforms and guarantee a profit (or minimize maximum loss).

## Core Concepts

### Dutch Book / Arbitrage

An arbitrage opportunity exists when the sum of "all outcomes" prices across markets falls below 1.0. In this scenario, buying all outcomes guarantees a risk-free profit.

**Example:**

- Market A: YES @ $0.40, NO @ $0.60 (sum = $1.00)
- Market B: YES @ $0.65, NO @ $0.30 (sum = $0.95)

Optimal strategy:

- Buy YES from Market A ($0.40)
- Buy NO from Market B ($0.30)
- **Total investment:** $0.70
- **Guaranteed return:** $1.00 (one outcome must occur)
- **Risk-free profit:** $0.30 (42.9% ROI)

### Opportunity Types

The detector classifies opportunities into three categories:

#### ✓ Arbitrage (Risk-Free Profit)

- Minimum profit > 0 in all scenarios
- No unfavorable outcomes
- Guaranteed return on investment
- Example: Dutch book scenario above

#### ⚠ Scalp (Conditional Profit)

- Profit depends on favorable outcome
- Minimum profit ≤ 0
- Positive expected value if outcome probabilities are favorable
- Used for hedging and position taking

#### ⊘ Hedge (Risk Mitigation)

- Reduces maximum loss
- Expected loss in all scenarios
- Useful for portfolio protection
- Not tradable for standalone profit

## API Usage

### Initialization

```python
from pm_arb.arbitrage_detector import ArbitrageDetector
from pm_arb.sql_storage import init_db

# Create detector with thresholds
detector = ArbitrageDetector(
    min_similarity=0.70,  # Minimum match quality [0, 1]
    min_profit_threshold=0.01,  # Minimum profit in dollars
)

# Register markets for analysis
detector.register_markets(markets_list)
```

### Detecting Opportunities

```python
# Find all opportunities above similarity threshold
opportunities = detector.detect_opportunities(
    session,
    min_similarity=0.70
)

# Get best opportunities by profit
best = detector.find_best_opportunity(session, limit=5)

# Get summary report
summary = detector.summarize_opportunities(opportunities)
print(summary)
```

### Opportunity Object

Each `ArbitrageOpportunity` contains:

```python
opp = opportunities[0]

# Markets and contracts
opp.source_a, opp.market_id_a    # Market A identifiers
opp.source_b, opp.market_id_b    # Market B identifiers
opp.yes_contract_a, opp.no_contract_a    # Contracts in market A
opp.yes_contract_b, opp.no_contract_b    # Contracts in market B

# Profit metrics
opp.min_profit      # Minimum guaranteed profit
opp.max_profit      # Maximum possible profit
opp.roi_pct         # Return on investment percentage
opp.total_investment # Capital required

# Quality metrics
opp.match_similarity     # How well markets are matched [0, 1]
opp.profit_if_yes       # Profit if YES outcome occurs
opp.profit_if_no        # Profit if NO outcome occurs

# Classification
opp.is_arbitrage        # True if risk-free profit
opp.is_scalp            # True if conditional profit
opp.arbitrage_type      # "both_sides", "scalp", or "hedge"
opp.break_even_spread   # Spread needed for profitability

# Display
summary = opp.summary()  # Human-readable text summary
```

## CLI Usage

### Find Arbitrage Opportunities

```bash
# Basic usage - find opportunities in database
python scripts/find_arbitrage.py --db pm_arb.db

# Find arbitrage with minimum 60% match quality
python scripts/find_arbitrage.py --db pm_arb.db --min-similarity 0.60

# Find only risk-free arbitrage with $0.10+ profit
python scripts/find_arbitrage.py --db pm_arb.db \
  --min-profit 0.10 \
  --limit 5

# Show top 20 opportunities with JSON output
python scripts/find_arbitrage.py --db pm_arb.db \
  --format json \
  --limit 20 \
  > opportunities.json

# Fetch fresh market data and analyze
python scripts/find_arbitrage.py --fetch --min-similarity 0.75

# Show detailed contract prices
python scripts/find_arbitrage.py --details --min-profit 0.05
```

### CLI Options

| Option             | Default     | Description                     |
| ------------------ | ----------- | ------------------------------- |
| `--db`             | `pm_arb.db` | Path to SQLite database         |
| `--min-similarity` | `0.70`      | Minimum match quality [0, 1]    |
| `--min-profit`     | `0.01`      | Minimum profit in dollars       |
| `--min-roi`        | `0.0`       | Minimum ROI percentage          |
| `--limit`          | `10`        | Maximum opportunities to show   |
| `--format`         | `text`      | Output format: `text` or `json` |
| `--fetch`          | -           | Fetch fresh market data first   |
| `--details`        | -           | Show contract price details     |

## Algorithm

### Detection Pipeline

1. **Market Matching**: Identify matched pairs using similarity scores
2. **Binary Market Check**: Filter to binary (YES/NO) markets only
3. **Contract Extraction**: Extract YES and NO contracts from both markets
4. **Price Calculation**: Get ask prices for cost calculation
5. **Optimal Selection**: Choose cheapest YES and cheapest NO across markets
6. **Profit Calculation**: Compute min/max profit and ROI
7. **Filtering**: Apply thresholds (similarity, profit, ROI)
8. **Sorting**: Order by minimum profit (best opportunities first)

### Price Logic

For each matched pair with binary contracts:

1. Extract:

   - `yes_a_price` = Cost to buy YES in market A
   - `no_a_price` = Cost to buy NO in market A
   - `yes_b_price` = Cost to buy YES in market B
   - `no_b_price` = Cost to buy NO in market B

2. Choose optimal prices:

   - `yes_price` = min(yes_a_price, yes_b_price)
   - `no_price` = min(no_a_price, no_b_price)

3. Calculate profit:

   - `total_investment` = yes_price + no_price
   - `guaranteed_return` = 1.0 (one outcome always occurs)
   - `min_profit` = guaranteed_return - total_investment

4. Determine type:
   - **Arbitrage**: min_profit > 0 (risk-free)
   - **Hedge**: min_profit ≤ 0 (requires favorable outcome)

## Data Requirements

The arbitrage detector requires:

### Markets

- `source`: Platform name (e.g., "kalshi", "polymarket")
- `market_id`: Unique market identifier
- `name`: Market question
- `category`: Optional category
- `contracts`: List of contract outcomes

### Contracts

- `source`, `market_id`, `contract_id`: Identifiers
- `name`: Contract name (e.g., "YES", "NO")
- `side`: Outcome side (typically "YES" or "NO")
- `outcome_type`: "binary" for detection to work
- `price_ask`: Ask price (cost to buy) [0, 1]
- `price_bid`: Bid price (sell price) [0, 1]
- `last_price`: Last traded price [0, 1]

### Matched Pairs

- `source_a`, `market_id_a`: First market identifiers
- `source_b`, `market_id_b`: Second market identifiers
- `similarity`: Match quality score [0, 1]
- Other scores: Optional but recommended

## Integration with Matching

Arbitrage detection sits on top of the matching system:

```python
# 1. Find matches using MarketMatcher
matcher = MarketMatcher()
matches = matcher.find_matches(markets)

# 2. Persist matches to database (optional)
for match in matches:
    save_matched_pair(session, ...)

# 3. Detect arbitrage from persisted pairs
detector = ArbitrageDetector()
detector.register_markets(markets)
opportunities = detector.detect_opportunities(session)
```

## Performance Considerations

### Efficiency

- **Market Loading**: O(n) to load and index n markets
- **Opportunity Detection**: O(m) to analyze m matched pairs
- **Overall**: O(n + m) for complete analysis

### Scaling

- Works efficiently with 100s of markets
- Scales to 1000s of matched pairs
- Minimal memory footprint (dataclass-based)

### Optimization Tips

1. **Filter by similarity**: Use `--min-similarity 0.80+` for high-quality matches only
2. **Set profit thresholds**: Use `--min-profit` to reduce noise
3. **Limit results**: Use `--limit` to focus on top opportunities
4. **Database indexing**: Matched pairs table is indexed on source/market_id

## Testing

Comprehensive test suite with 21 tests covering:

```bash
# Run arbitrage detector tests
PYTHONPATH=src pytest tests/test_arbitrage_detector.py -v

# Test categories:
# - Detector initialization and market registration
# - Binary market detection and validation
# - YES/NO contract extraction
# - Arbitrage calculation and profit computation
# - Opportunity detection from database
# - Opportunity summarization and filtering
# - Edge cases (missing data, invalid prices, etc.)
```

## Typical Workflow

### Finding Arbitrage Opportunities

```bash
# 1. Load or fetch market data
python scripts/demo_fetch.py

# 2. Create matched pairs
python scripts/match_markets.py

# 3. Find arbitrage opportunities
python scripts/find_arbitrage.py --min-similarity 0.75 --min-profit 0.05

# 4. Export for further analysis
python scripts/find_arbitrage.py --format json > opportunities.json
```

### Programmatic Analysis

```python
from pm_arb.sql_storage import init_db, MarketORM
from pm_arb.arbitrage_detector import ArbitrageDetector

# Load database and markets
engine, SessionLocal = init_db("pm_arb.db")
session = SessionLocal()

markets_orm = session.query(MarketORM).all()
markets = [convert_to_unified(m) for m in markets_orm]

# Find opportunities
detector = ArbitrageDetector(min_similarity=0.75)
detector.register_markets(markets)
opps = detector.detect_opportunities(session)

# Analyze top opportunities
for opp in opps[:5]:
    print(f"{opp.source_a} vs {opp.source_b}: ${opp.min_profit:.2f} profit")
    if opp.is_arbitrage:
        print("  ✓ Risk-free!")

session.close()
```

## Common Patterns

### Find High-ROI Arbitrage Only

```python
opportunities = detector.detect_opportunities(session)
high_roi = [o for o in opportunities if o.roi_pct > 5.0 and o.is_arbitrage]
```

### Filter by Market Source

```python
kalshi_opps = [o for o in opportunities if o.source_a == "kalshi"]
cross_source = [o for o in opportunities
                if o.source_a != o.source_b]
```

### Sort by Different Metrics

```python
# Sort by ROI
by_roi = sorted(opps, key=lambda x: x.roi_pct, reverse=True)

# Sort by investment required
by_size = sorted(opps, key=lambda x: x.total_investment)

# Sort by match quality
by_quality = sorted(opps, key=lambda x: x.match_similarity, reverse=True)
```

## Limitations

1. **Binary Markets Only**: Current implementation handles YES/NO markets only
2. **Perfect Execution**: Assumes instant execution at quoted prices
3. **No Transaction Costs**: Doesn't account for fees, slippage, or latency
4. **Point-in-Time**: Analysis reflects snapshot prices; markets move fast
5. **Cross-Platform Complexity**: Real execution requires account on both platforms

## Future Enhancements

- [ ] Multi-outcome market support (e.g., 3+ outcomes)
- [ ] Transaction cost modeling (fees, slippage, latency)
- [ ] Real-time opportunity monitoring
- [ ] Automated execution integration
- [ ] Portfolio optimization for multi-leg trades
- [ ] Historical opportunity tracking and analysis
- [ ] Confidence scoring based on liquidity depth
- [ ] Market state caching and invalidation
