# Market Matching Layer

## Overview

The market matching layer is a machine learning-based system that links similar markets across different prediction platforms (Kalshi, Polymarket, PredictIt). This enables arbitrage detection, pricing analysis, and cross-platform market comparisons.

## Key Features

- **TF-IDF Text Similarity**: Character-level n-grams (bigrams/trigrams) to match market names across textual variations
- **Cosine Similarity**: Semantic similarity scoring for market names
- **Fuzzy String Matching**: Fallback fuzzy matching using difflib's SequenceMatcher for contract names
- **Multi-factor Scoring**: Combines name similarity, category match, contract structure, and temporal proximity
- **Confidence Levels**: Automatic confidence assessment (low/medium/high)
- **Contract Matching**: Identifies individual contracts that correspond across platforms

## Architecture

### Core Classes

#### `MatchResult`

Represents a single match between two markets with detailed scoring information.

```python
@dataclass
class MatchResult:
    market_a: UnifiedMarket
    market_b: UnifiedMarket
    match_score: float              # Overall score [0, 1]
    name_similarity: float          # TF-IDF cosine similarity
    category_similarity: float      # Exact/partial category match
    contract_similarity: float      # Structure & outcome type match
    temporal_proximity: float       # Time window match [0, 1]
    matching_contracts: List[...]   # Paired contracts
    confidence: str                 # "high", "medium", "low"
```

#### `MarketMatcher`

Main class for finding matches between markets.

**Constructor Parameters:**

```python
MarketMatcher(
    name_weight=0.4,              # Weight for name similarity
    category_weight=0.2,          # Weight for category match
    contract_weight=0.3,          # Weight for contract structure
    temporal_weight=0.1,          # Weight for temporal proximity
    min_score_threshold=0.5,      # Minimum score to include match
    max_days_apart=7              # Max days between event times
)
```

## Scoring Algorithm

The overall match score is a weighted combination of four components:

```
overall_score = (0.4 × name_sim) + (0.2 × category_sim) + (0.3 × contract_sim) + (0.1 × temporal_sim)
```

### 1. Name Similarity (40%)

Uses **TF-IDF vectorization** with character-level n-grams (2-3 characters):

```
- Clean text: lowercase, remove special chars
- Vectorize: fit on all market names, generate character bigrams/trigrams
- Score: cosine similarity between TF-IDF vectors
- Range: [0, 1]
```

Example:

- "Bitcoin close above $100k" vs "Bitcoin to exceed 100k" → **0.73 similarity**

### 2. Category Similarity (20%)

Exact or partial category matching:

```
- Exact match: 1.0
- Partial match (substring): 0.7
- No match: 0.0
- Missing category: 0.5 (neutral)
```

Examples:

- "Crypto" vs "Cryptocurrency" → **0.7**
- "Politics" vs "Politics" → **1.0**
- "Politics" vs "Sports" → **0.0**

### 3. Contract Similarity (30%)

Compares contract structure across markets:

```
contract_sim = (0.6 × outcome_type_match) + (0.4 × count_similarity)

outcome_type_match = common_types / all_types
count_similarity = 1 - |count_a - count_b| / max(count_a, count_b)
```

Examples:

- Both binary with same contracts → **1.0**
- One binary (2 contracts), one multi (5 contracts) → **0.3-0.6**
- Different outcome types → **0.0-0.3**

### 4. Temporal Proximity (10%)

Matches markets with similar event dates:

```
if dates_identical: 1.0
if days_apart ≤ max_days_apart: 1.0 - (days_apart / max_days_apart)
else: 0.0
```

Missing dates treated as neutral (0.5).

## Confidence Scoring

Automatic confidence assessment based on multiple signals:

- **HIGH**: score > 0.8 AND name_sim > 0.7 AND contracts matched
- **MEDIUM**: (score > 0.65) OR (score > 0.5 AND contracts matched)
- **LOW**: Otherwise

## Usage Examples

### Basic Usage

```python
from pm_arb.matcher import MarketMatcher
from pm_arb.api.models import UnifiedMarket

matcher = MarketMatcher()

# Single pair matching
result = matcher.match_single_pair(market_a, market_b)
print(f"Score: {result.match_score:.3f}, Confidence: {result.confidence}")

# Multiple markets across sources
kalshi_markets = [...]
polymarket_markets = [...]

matches = matcher.find_matches(
    kalshi_markets,
    polymarket_markets,
    cross_source_only=True  # Only match different sources
)

# Sort by confidence and score
high_confidence = [m for m in matches if m.confidence == "high"]
```

### CLI Usage

Find and display matching markets:

```bash
# All matches with medium+ confidence
python scripts/match_markets.py --db pm_arb_demo.db --min-confidence medium

# Show matching contracts
python scripts/match_markets.py --db pm_arb_demo.db --show-contracts

# Adjust minimum score threshold
python scripts/match_markets.py --db pm_arb_demo.db --min-score 0.7
```

### Create Sample Data

```bash
# Add test markets designed to demonstrate matching
python scripts/create_sample_markets.py --db pm_arb_demo.db --reset

# Then run the matcher
python scripts/match_markets.py --db pm_arb_demo.db --show-contracts
```

## Integration with Arbitrage Detection

The matcher enables several arbitrage strategies:

1. **Price Discrepancy Detection**: Once markets are matched, compare bid-ask spreads and mid-prices across platforms
2. **Market Efficiency Tracking**: Monitor which platform prices markets more efficiently
3. **Hedging Opportunities**: Match complementary contracts (YES vs NO) across platforms for risk-free positions

Example integration:

```python
from pm_arb.matcher import MarketMatcher
from pm_arb.sql_storage import init_db, load_market

# Load all markets from DB
matcher = MarketMatcher()
matches = matcher.find_matches(all_markets, cross_source_only=True)

# Filter high-confidence matches
for match in matches:
    if match.confidence != "high":
        continue

    # Compare prices on market A vs B
    if match.market_a.contracts and match.market_b.contracts:
        # Find price discrepancy
        for contract_a, contract_b in match.matching_contracts:
            if contract_a.price_bid and contract_b.price_ask:
                if contract_b.price_ask < contract_a.price_bid:
                    # Arbitrage opportunity!
                    profit = contract_a.price_bid - contract_b.price_ask
                    print(f"BUY on {contract_b.source} @ {contract_b.price_ask}, "
                          f"SELL on {contract_a.source} @ {contract_a.price_bid}")
```

## Performance Characteristics

- **Time Complexity**: O(n × m) where n and m are market list sizes
  - TF-IDF vectorization: O((n+m) × t) where t is average name length
  - Similarity computation: O(n × m × features)
- **Space Complexity**: O(n + m) for vectorizer and similarity matrices

For typical use cases (100-1000 markets):

- Vectorization: <100ms
- Similarity computation: <50ms
- Contract matching: <10ms
- Total: <200ms for 1000 markets

## Configuration Tips

### Stricter Matching (Fewer False Positives)

```python
matcher = MarketMatcher(
    min_score_threshold=0.75,  # Raise threshold
    name_weight=0.6,           # Weight names more heavily
    contract_weight=0.2,       # Weight contract structure less
)
```

### Looser Matching (Fewer False Negatives)

```python
matcher = MarketMatcher(
    min_score_threshold=0.4,   # Lower threshold
    temporal_weight=0.05,      # Ignore temporal differences
    category_weight=0.1,       # Reduce category importance
)
```

### Different Event Timeframes

```python
matcher = MarketMatcher(
    max_days_apart=30,         # Allow 30-day difference instead of 7
)
```

## Testing

Run the comprehensive test suite:

```bash
# All matcher tests
PYTHONPATH=src python -m pytest tests/test_matcher.py -v

# Specific test class
PYTHONPATH=src python -m pytest tests/test_matcher.py::TestMarketMatcher -v

# With coverage
PYTHONPATH=src python -m pytest tests/test_matcher.py --cov=pm_arb.matcher
```

Current test coverage:

- ✅ Initialization and parameter validation
- ✅ Text cleaning and fuzzy matching
- ✅ Category similarity scoring
- ✅ Contract similarity scoring
- ✅ Temporal proximity scoring
- ✅ Confidence level computation
- ✅ Single pair and batch matching
- ✅ Cross-source filtering

## Future Enhancements

1. **Embedding-based Matching**: Use sentence transformers or other embeddings for deeper semantic understanding
2. **Probabilistic Matching**: Bayesian network to combine multiple signals with uncertainty
3. **Active Learning**: User feedback loop to improve matcher over time
4. **Custom Matchers**: Domain-specific matchers for sports, politics, economics
5. **Caching**: Memoize vectorizer and similarity matrices for repeated queries
6. **Parallel Processing**: Use joblib to parallelize matching for large datasets
7. **Evolutionary Algorithm**: Train weights using genetic algorithm on ground truth matches

## Dependencies

- `scikit-learn>=1.7.2`: TF-IDF vectorization and cosine similarity
- `numpy<2`: Numerical computing
- `python-dateutil`: Parsing event times
- `pandas`: Optional, for exporting results to CSV/Excel

All dependencies are in `requirements.txt`.
