# Market Matching Layer - Quick Reference

## Installation & Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "from pm_arb.matcher import MarketMatcher; print('✓ Ready!')"
```

## Quick Start

### 1. Create Test Data

```bash
python scripts/create_sample_markets.py --db pm_arb_demo.db --reset
```

### 2. Find Matching Markets

```bash
python scripts/match_markets.py --db pm_arb_demo.db --show-contracts
```

### 3. Detect Arbitrage Opportunities

```bash
python scripts/find_arbitrage.py --db pm_arb_demo.db --min-spread 5.0
```

## Programmatic Usage

### Basic Matching

```python
from pm_arb.matcher import MarketMatcher
from pm_arb.api.models import UnifiedMarket, UnifiedContract

# Create matcher
matcher = MarketMatcher()

# Find matches
matches = matcher.find_matches(markets_a, markets_b, cross_source_only=True)

# Use results
for match in matches:
    print(f"Match: {match.market_a.name} ↔ {match.market_b.name}")
    print(f"Score: {match.match_score:.3f}")
    print(f"Confidence: {match.confidence}")

    for contract_a, contract_b in match.matching_contracts:
        print(f"  {contract_a.name} ↔ {contract_b.name}")
```

### Custom Configuration

```python
matcher = MarketMatcher(
    name_weight=0.5,           # Emphasize name matching
    contract_weight=0.2,       # De-emphasize contract structure
    min_score_threshold=0.7,   # Higher threshold for precision
    max_days_apart=14          # Allow 2-week event time difference
)
```

### With Database

```python
from pm_arb.sql_storage import init_db, MarketORM, load_market

# Load markets from database
engine, SessionLocal = init_db("sqlite:///pm_arb_demo.db")
session = SessionLocal()

market_orms = session.query(MarketORM).all()
markets = [load_market(session, m.source, m.market_id) for m in market_orms]

# Run matching
matcher = MarketMatcher()
matches = matcher.find_matches(markets, cross_source_only=True)

# Filter by confidence
high_confidence = [m for m in matches if m.confidence == "high"]
```

## CLI Reference

### match_markets.py

```bash
# Show all matches
python scripts/match_markets.py --db pm_arb_demo.db

# Show matches with contracts
python scripts/match_markets.py --db pm_arb_demo.db --show-contracts

# Filter by score
python scripts/match_markets.py --db pm_arb_demo.db --min-score 0.7

# Filter by confidence
python scripts/match_markets.py --db pm_arb_demo.db --min-confidence high

# Combine filters
python scripts/match_markets.py --db pm_arb_demo.db \
  --min-score 0.6 \
  --min-confidence medium \
  --show-contracts
```

### find_arbitrage.py

```bash
# Find spreads > 5%
python scripts/find_arbitrage.py --db pm_arb_demo.db --min-spread 5.0

# Find spreads > 1%
python scripts/find_arbitrage.py --db pm_arb_demo.db --min-spread 1.0

# Custom database
python scripts/find_arbitrage.py --db other.db --min-spread 3.0
```

### create_sample_markets.py

```bash
# Add samples (keeps existing)
python scripts/create_sample_markets.py --db pm_arb_demo.db

# Reset and add samples
python scripts/create_sample_markets.py --db pm_arb_demo.db --reset
```

## Matching Scores Explained

### Overall Score (0-1)

- **0.8-1.0**: Excellent match (high confidence)
- **0.6-0.8**: Good match (medium confidence)
- **0.4-0.6**: Possible match (low confidence)
- **<0.4**: Not a match

### Component Scores

- **Name Similarity**: How similar market names are (TF-IDF cosine)
- **Category Similarity**: How well categories align
- **Contract Similarity**: How similar the contract structures are
- **Temporal Proximity**: How close the event dates are

## Confidence Levels

### HIGH ✓✓

- Score > 0.8
- Name similarity > 0.7
- Contracts matched
- Use for: Reliable arbitrage detection

### MEDIUM ✓

- Score > 0.65 OR (score > 0.5 with contract matches)
- Use for: Secondary verification

### LOW

- Lower scores
- Use for: Manual review only

## Common Tasks

### Find All Bitcoin Markets

```python
from pm_arb.matcher import MarketMatcher

bitcoin_markets = [m for m in markets if "bitcoin" in m.name.lower()]
matches = matcher.find_matches(bitcoin_markets, cross_source_only=True)
```

### Find Matches Between Specific Platforms

```python
kalshi = [m for m in markets if m.source == "kalshi"]
polymarket = [m for m in markets if m.source == "polymarket"]
matches = matcher.find_matches(kalshi, polymarket)
```

### Get Top 10 Matches

```python
matches = matcher.find_matches(markets_a, markets_b)
top_10 = matches[:10]
```

### Find Binary Markets Only

```python
binary_markets = [
    m for m in markets
    if all(c.outcome_type == "binary" for c in m.contracts)
]
matches = matcher.find_matches(binary_markets)
```

### Calculate Potential Profit

```python
from pm_arb.matcher import MarketMatcher

matches = matcher.find_matches(markets)

for match in matches:
    for contract_a, contract_b in match.matching_contracts:
        if contract_a.price_bid and contract_b.price_ask:
            profit = contract_a.price_bid - contract_b.price_ask
            if profit > 0:
                print(f"Arbitrage: Buy @ {contract_b.price_ask}, "
                      f"Sell @ {contract_a.price_bid}, "
                      f"Profit: ${profit:.4f}")
```

## Testing

```bash
# Run all matcher tests
PYTHONPATH=src python -m pytest tests/test_matcher.py -v

# Run specific test
PYTHONPATH=src python -m pytest tests/test_matcher.py::TestMarketMatcher::test_fuzzy_match_identical -v

# Run with coverage
PYTHONPATH=src python -m pytest tests/test_matcher.py --cov=pm_arb.matcher --cov-report=html
```

## Troubleshooting

### ImportError: No module named 'pm_arb'

```bash
# Solution: Set PYTHONPATH
PYTHONPATH=src python scripts/match_markets.py --db pm_arb_demo.db
```

### NumPy Version Error

```bash
# Solution: Downgrade NumPy
pip install "numpy<2"
```

### No matches found

- Check `--min-score` threshold (lower it)
- Check market data is in database
- Verify markets are from different sources
- Review match scores for low-confidence matches

### Low match scores

- Markets may be too different (different event times, categories)
- Adjust weights with custom `MarketMatcher` configuration
- Consider lowering `min_score_threshold`

## Performance Tips

### For Large Datasets (10k+ markets)

1. Filter markets by category first
2. Use higher `min_score_threshold` (e.g., 0.7)
3. Consider parallel processing
4. Cache vectorizer for repeated runs

### Memory Optimization

```python
# Process in batches instead of all at once
batch_size = 1000
for i in range(0, len(markets), batch_size):
    batch = markets[i:i+batch_size]
    matches = matcher.find_matches(batch)
```

## Further Reading

- `docs/MATCHING.md` - Complete documentation
- `MATCHING_IMPLEMENTATION.md` - Implementation details
- `tests/test_matcher.py` - Usage examples in tests
- `src/pm_arb/matcher.py` - Source code with docstrings

## Support

For issues or questions:

1. Check the documentation files
2. Review test examples
3. Check GitHub issues
4. Run diagnostics:
   ```bash
   python -m pytest tests/test_matcher.py -v
   ```

---

**Quick Links:**

- 🔗 [Full Documentation](docs/MATCHING.md)
- 🧪 [Tests](tests/test_matcher.py)
- 💡 [Implementation Details](MATCHING_IMPLEMENTATION.md)
- 📝 [Source Code](src/pm_arb/matcher.py)
