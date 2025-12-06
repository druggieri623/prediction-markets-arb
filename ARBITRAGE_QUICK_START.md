"""Quick Reference Guide for Arbitrage Detection"""

# Arbitrage Detector - Quick Reference

## Installation & Setup

```bash
# Navigate to project
cd /Users/daveruggieri/Projects/prediction-markets-arb

# Activate virtual environment
source .venv/bin/activate

# Ensure dependencies installed
pip install -r requirements.txt
```

## CLI Quick Start

### Basic Usage

```bash
# Find all opportunities
python scripts/find_arbitrage.py --db pm_arb.db

# Find high-quality matches only (80%+ similarity)
python scripts/find_arbitrage.py --db pm_arb.db --min-similarity 0.80

# Find profitable opportunities ($0.10+ profit)
python scripts/find_arbitrage.py --db pm_arb.db --min-profit 0.10

# Find 5% ROI+ opportunities
python scripts/find_arbitrage.py --db pm_arb.db --min-roi 5.0

# Show top 20 opportunities
python scripts/find_arbitrage.py --db pm_arb.db --limit 20

# Export to JSON
python scripts/find_arbitrage.py --db pm_arb.db --format json > opportunities.json

# Show detailed contract prices
python scripts/find_arbitrage.py --db pm_arb.db --details

# Combined filtering
python scripts/find_arbitrage.py \
  --db pm_arb.db \
  --min-similarity 0.75 \
  --min-profit 0.05 \
  --limit 10 \
  --format json
```

## Python API Quick Start

### Basic Workflow

```python
from pm_arb.arbitrage_detector import ArbitrageDetector
from pm_arb.sql_storage import init_db, MarketORM

# Initialize database
engine, SessionLocal = init_db("sqlite:///pm_arb.db")
session = SessionLocal()

# Load markets
markets_orm = session.query(MarketORM).all()
markets = [convert_to_unified(m) for m in markets_orm]

# Create detector
detector = ArbitrageDetector(
    min_similarity=0.70,
    min_profit_threshold=0.01
)

# Register markets
detector.register_markets(markets)

# Find opportunities
opportunities = detector.detect_opportunities(session)

# Display results
for opp in opportunities[:5]:
    print(opp.summary())

session.close()
```

### Find Best Opportunities

```python
# Get top 5 by profit
best = detector.find_best_opportunity(session, limit=5)

# Display summary
summary = detector.summarize_opportunities(best)
print(summary)

# Access individual metrics
for opp in best:
    print(f"${opp.min_profit:.2f} profit ({opp.roi_pct:.1f}% ROI)")
    print(f"  Type: {opp.arbitrage_type}")
    print(f"  Quality: {opp.match_similarity:.1%}")
```

### Filter Opportunities

```python
# Risk-free arbitrage only
arbs = [o for o in opportunities if o.is_arbitrage]

# High ROI opportunities
high_roi = [o for o in opportunities if o.roi_pct > 5.0]

# By market source
kalshi_opps = [o for o in opportunities if o.source_a == "kalshi"]

# By profit
over_dollar = [o for o in opportunities if o.min_profit > 1.0]

# Combined
best_arbs = [o for o in opportunities 
             if o.is_arbitrage and o.roi_pct > 2.0]
```

## Understanding Results

### Opportunity Output

```
KALSHI/event-a ↔ POLYMARKET/event-b
Type: BOTH_SIDES | Match Quality: 95.0%
Min Profit: $0.30 | Max Profit: $0.30
ROI: 42.86% | Investment: $0.70
✓ ARBITRAGE (risk-free profit opportunity)
Notes: Buy YES at A ($0.40), NO at B ($0.30)
```

### Opportunity Attributes

| Attribute | Meaning | Example |
|-----------|---------|---------|
| `min_profit` | Minimum guaranteed profit | $0.30 |
| `max_profit` | Maximum possible profit | $0.30 |
| `roi_pct` | Return on investment | 42.86% |
| `total_investment` | Capital required | $0.70 |
| `match_similarity` | Market matching quality | 0.95 (95%) |
| `is_arbitrage` | Risk-free? | True |
| `arbitrage_type` | Opportunity type | "both_sides" |

### Opportunity Types

**✓ Arbitrage** (Risk-Free)
- Buy YES cheaply on one platform
- Buy NO cheaply on another
- Guaranteed profit regardless of outcome
- Can execute immediately

**⚠ Scalp** (Conditional)
- Profit depends on favorable outcome
- Higher potential returns
- Requires favorable outcome to be true
- More risk but can be lucrative

**⊘ Hedge** (Risk Mitigation)
- Expected loss in all scenarios
- Reduces maximum loss
- Used for portfolio protection
- Not executable for standalone profit

## CLI Options Reference

```bash
--db PATH              # Database path (default: pm_arb.db)
--min-similarity 0.75  # Min quality [0, 1] (default: 0.70)
--min-profit 0.01      # Min profit $ (default: $0.01)
--min-roi 2.0          # Min ROI % (default: 0.0)
--limit 10             # Max to show (default: 10)
--format json          # Output format (default: text)
--fetch                # Fetch fresh market data
--details              # Show contract prices
--help                 # Show help message
```

## Common Patterns

### Find Best Arbitrage

```bash
python scripts/find_arbitrage.py \
  --min-similarity 0.80 \
  --min-profit 0.10 \
  --limit 5
```

### Export for Excel

```bash
python scripts/find_arbitrage.py \
  --format json \
  --details \
  > opportunities.json

# Then import JSON into Excel/Google Sheets
```

### Monitor Opportunities

```bash
# Run periodically to check for new opportunities
while true; do
  python scripts/find_arbitrage.py --min-profit 0.05
  sleep 60
done
```

### Filter by Source

```python
# Kalshi vs PolyMarket
cross_platform = [
    o for o in opportunities
    if (o.source_a == "kalshi" and o.source_b == "polymarket")
    or (o.source_a == "polymarket" and o.source_b == "kalshi")
]
```

## Typical Workflow

1. **Load Market Data**
   ```bash
   python scripts/demo_fetch.py
   ```

2. **Find Matches**
   ```bash
   python scripts/match_markets.py --db pm_arb.db
   ```

3. **Detect Arbitrage**
   ```bash
   python scripts/find_arbitrage.py --db pm_arb.db
   ```

4. **Review & Execute**
   - Check profit/ROI metrics
   - Verify match quality
   - Execute trades on platforms
   - Track results

## Testing

```bash
# Run all tests
PYTHONPATH=src pytest tests/ -v

# Run arbitrage tests only
PYTHONPATH=src pytest tests/test_arbitrage_detector.py -v

# Run with coverage
PYTHONPATH=src pytest tests/ --cov=src/pm_arb/arbitrage_detector.py
```

## Data Requirements

### Markets Need
- `source`: Platform (kalshi, polymarket, predictit)
- `market_id`: Unique identifier
- `name`: Market question
- `contracts`: List of outcomes

### Contracts Need
- `source`, `market_id`: Identifiers
- `side`: "YES" or "NO"
- `outcome_type`: "binary"
- `price_ask`: Ask price [0, 1]

### Matched Pairs Need
- `source_a`, `market_id_a`: First market
- `source_b`, `market_id_b`: Second market
- `similarity`: Match quality [0, 1]

## Troubleshooting

### No opportunities found
- ✓ Lower `--min-similarity` (try 0.60-0.70)
- ✓ Lower `--min-profit` (try $0.01)
- ✓ Ensure matched pairs exist in database
- ✓ Check market data has prices

### Wrong results
- ✓ Verify binary markets (YES/NO only)
- ✓ Check price data [0, 1] range
- ✓ Ensure matched pair quality is good
- ✓ Review contract side names

### Performance issues
- ✓ Use `--limit` to reduce output
- ✓ Use `--min-similarity 0.80+` for fewer pairs
- ✓ Index database tables
- ✓ Consider batch processing

## Performance Tips

1. **Filter aggressively**
   - Use `--min-similarity 0.75+` for high-quality matches
   - Set `--min-profit` to realistic thresholds
   - Use `--limit` to focus on best opportunities

2. **Database optimization**
   - Keep database indexed
   - Archive old pairs periodically
   - Use `--db` to specify efficient storage

3. **Execution strategy**
   - Check opportunities frequently
   - Execute highest ROI first
   - Monitor market movements
   - Exit quickly if spreads change

## Key Metrics

**Perfect Arbitrage Score**
```
Match Quality: ≥ 0.90     (High confidence match)
Min Profit: ≥ $0.10      (Meaningful profit)
ROI: ≥ 5.0%             (Good return)
Investment: ≤ $10        (Reasonable capital)
Type: arbitrage          (Risk-free)
```

**Good Opportunity Score**
```
Match Quality: ≥ 0.75    (Decent confidence)
Min Profit: ≥ $0.05      (Profitable)
ROI: ≥ 2.0%             (Worthwhile)
Investment: ≤ $20        (Manageable)
Type: arbitrage or scalp (Profitable)
```

## Resources

- **Full Documentation**: `docs/ARBITRAGE_DETECTION.md`
- **Implementation Summary**: `ARBITRAGE_DETECTOR_SUMMARY.md`
- **Source Code**: `src/pm_arb/arbitrage_detector.py`
- **Tests**: `tests/test_arbitrage_detector.py`
- **CLI Tool**: `scripts/find_arbitrage.py`

## Support

For issues or questions:
1. Check documentation in `docs/ARBITRAGE_DETECTION.md`
2. Review test examples in `tests/test_arbitrage_detector.py`
3. Check script help: `python scripts/find_arbitrage.py --help`
4. Verify data in database with other tools
