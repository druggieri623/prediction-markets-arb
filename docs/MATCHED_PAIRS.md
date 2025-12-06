# Matched Market Pairs Persistence

## Overview

The matched market pairs feature allows you to persist market matches to a database table for:
- **Historical tracking**: Keep a record of all discovered matches
- **Manual confirmation**: Mark matches as confirmed by humans
- **Analysis**: Query and analyze match patterns over time
- **Integration**: Link matched pairs for arbitrage detection

## Database Schema

### `matched_market_pairs` Table

```sql
CREATE TABLE matched_market_pairs (
    id INTEGER PRIMARY KEY,
    source_a VARCHAR NOT NULL,          -- Source of market A (kalshi, polymarket, etc)
    market_id_a VARCHAR NOT NULL,       -- Market ID for market A
    source_b VARCHAR NOT NULL,          -- Source of market B
    market_id_b VARCHAR NOT NULL,       -- Market ID for market B
    
    -- Match quality scores
    similarity FLOAT NOT NULL,          -- Overall match score [0, 1]
    classifier_probability FLOAT,       -- ML classifier probability [0, 1]
    name_similarity FLOAT,              -- Name matching score
    category_similarity FLOAT,          -- Category matching score
    temporal_proximity FLOAT,           -- Temporal alignment score
    
    -- Manual confirmation
    is_manual_confirmed BOOLEAN DEFAULT FALSE,
    confirmed_by VARCHAR,               -- User who confirmed (email, username)
    confirmed_at DATETIME,              -- When confirmed
    
    -- Metadata
    notes VARCHAR,                      -- Optional notes on match
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE (source_a, market_id_a, source_b, market_id_b)
);
```

**Key Features:**
- **Unique constraint**: Prevents duplicate pairs (with consistent ordering)
- **Pair ordering**: Automatically stores pairs in sorted order for consistency
- **Timestamps**: Tracks when pair was created and last updated
- **Confirmation tracking**: Records who confirmed and when

## Python API

### Save a Matched Pair

```python
from pm_arb.sql_storage import init_db, save_matched_pair

engine, SessionLocal = init_db("sqlite:///pm_arb.db")
session = SessionLocal()

# Save a matched pair
pair = save_matched_pair(
    session,
    source_a="kalshi",
    market_id_a="btc-1",
    source_b="polymarket",
    market_id_b="0xabc123",
    similarity=0.75,
    classifier_probability=0.82,
    name_similarity=0.65,
    category_similarity=0.85,
    temporal_proximity=1.0,
    notes="Bitcoin price markets"
)

# Updates are automatic - calling with same pair updates existing record
pair = save_matched_pair(
    session,
    source_a="kalshi",
    market_id_a="btc-1",
    source_b="polymarket",
    market_id_b="0xabc123",
    similarity=0.80,  # Updated score
)
```

### Confirm a Match

```python
from pm_arb.sql_storage import confirm_matched_pair

# Manually confirm a match
confirmed = confirm_matched_pair(
    session,
    source_a="kalshi",
    market_id_a="btc-1",
    source_b="polymarket",
    market_id_b="0xabc123",
    confirmed_by="alice@example.com",
    notes="Verified on chain data"
)
```

### Query Matched Pairs

```python
from pm_arb.sql_storage import get_matched_pairs

# Get all pairs
all_pairs = get_matched_pairs(session)

# Get high-confidence matches
strong_matches = get_matched_pairs(
    session,
    min_similarity=0.70
)

# Get pairs from specific source
kalshi_matches = get_matched_pairs(
    session,
    source_a="kalshi"
)

# Get only confirmed pairs
confirmed_matches = get_matched_pairs(
    session,
    confirmed_only=True
)

# Combine filters
high_value = get_matched_pairs(
    session,
    source_a="kalshi",
    min_similarity=0.75,
    confirmed_only=True
)

# Results are ordered by similarity descending
for pair in strong_matches:
    print(f"{pair.source_a}/{pair.market_id_a} ↔ {pair.source_b}/{pair.market_id_b}")
    print(f"Similarity: {pair.similarity:.2%}")
    print(f"Confirmed: {pair.is_manual_confirmed}")
```

## Command-Line Tools

### Persist Matches

Find matches and save them to the database:

```bash
# Find and persist all matches above 50% score
python scripts/persist_matches.py --db pm_arb_demo.db --min-score 0.5

# Include classifier probabilities
python scripts/persist_matches.py --db pm_arb_demo.db --use-classifier

# Clear existing matches before persisting new ones
python scripts/persist_matches.py --db pm_arb_demo.db --clear

# Show results after persisting
python scripts/persist_matches.py --db pm_arb_demo.db --show
```

**Options:**
- `--db` - Database path (default: pm_arb_demo.db)
- `--min-score` - Minimum match score to persist (default: 0.5)
- `--use-classifier` - Compute ML classifier probabilities
- `--clear` - Delete existing matches before saving new ones
- `--show` - Display persisted matches after saving

**Output:**
```
Loaded 6 markets

================================================================================
FINDING AND PERSISTING MATCHES
================================================================================

✓ Saved match #1
  kalshi/btc-1 ↔ polymarket/0xabc123
  Rule-based score: 64.84%

✓ Saved match #2
  kalshi/inf-1 ↔ predictit/5012
  Rule-based score: 73.64%

...
```

### View Persisted Matches

Query and display matches from database:

```bash
# Show all matches
python scripts/view_matches.py --db pm_arb_demo.db

# Filter by minimum score
python scripts/view_matches.py --db pm_arb_demo.db --min-score 0.70

# Show only confirmed matches
python scripts/view_matches.py --db pm_arb_demo.db --confirmed

# Filter by source
python scripts/view_matches.py --db pm_arb_demo.db --source-a kalshi --source-b polymarket

# Limit results
python scripts/view_matches.py --db pm_arb_demo.db --limit 10

# Output as JSON
python scripts/view_matches.py --db pm_arb_demo.db --json
```

**Options:**
- `--db` - Database path (default: pm_arb_demo.db)
- `--min-score` - Minimum similarity filter
- `--source-a` - Filter by first source
- `--source-b` - Filter by second source
- `--confirmed` - Show only confirmed matches
- `--limit` - Maximum number of results
- `--json` - Output as JSON instead of text

**Text Output:**
```
====================================================================================================
MATCHED MARKET PAIRS (Total: 3)
====================================================================================================

Match #1 ◯ unconfirmed
  Market A: kalshi       | btc-1
  Market B: polymarket   | 0xabc123

  Scores:
    Overall similarity: 64.84%
    Name similarity:    19.59%
    Category similar:   85.00%
    Temporal proximity: 100.00%

...
```

**JSON Output:**
```json
[
  {
    "source_a": "kalshi",
    "market_id_a": "btc-1",
    "source_b": "polymarket",
    "market_id_b": "0xabc123",
    "similarity": 0.6484,
    "classifier_probability": null,
    "name_similarity": 0.1959,
    "category_similarity": 0.85,
    "temporal_proximity": 1.0,
    "is_manual_confirmed": false,
    "confirmed_by": null,
    "notes": null,
    "created_at": "2025-12-05T22:35:00"
  }
]
```

## Example Workflow

### 1. Find and Persist Matches

```bash
# Run matcher to find and save all matches > 60% score
python scripts/persist_matches.py --db pm_arb_demo.db --min-score 0.6
```

### 2. Review Matches

```bash
# View high-confidence matches
python scripts/view_matches.py --db pm_arb_demo.db --min-score 0.7
```

### 3. Manually Confirm Matches (Python)

```python
from pm_arb.sql_storage import init_db, confirm_matched_pair

engine, SessionLocal = init_db("sqlite:///pm_arb_demo.db")
session = SessionLocal()

# Confirm a match after manual verification
confirm_matched_pair(
    session,
    "kalshi", "btc-1",
    "polymarket", "0xabc123",
    confirmed_by="trader@example.com",
    notes="Verified: same event, same resolution criteria"
)

session.close()
```

### 4. Analyze Confirmed Matches

```python
from pm_arb.sql_storage import init_db, get_matched_pairs

engine, SessionLocal = init_db("sqlite:///pm_arb_demo.db")
session = SessionLocal()

# Get all confirmed matches for arbitrage analysis
confirmed = get_matched_pairs(session, confirmed_only=True)

for pair in confirmed:
    print(f"Arbitrage opportunity:")
    print(f"  {pair.source_a}/{pair.market_id_a} vs {pair.source_b}/{pair.market_id_b}")
    print(f"  Confidence: {pair.similarity:.1%}")
    # Use these pairs for arbitrage detection
```

## Integration with Matcher and Classifier

### Full Pipeline

```python
from pm_arb.sql_storage import init_db, save_market, save_matched_pair
from pm_arb.matcher import MarketMatcher
from pm_arb.matcher_classifier import MatcherClassifier

# 1. Load markets from external sources
engine, SessionLocal = init_db("sqlite:///pm_arb.db")
session = SessionLocal()

# 2. Save markets to database
for market in markets:
    save_market(session, market)

# 3. Find matches using rule-based matcher
matcher = MarketMatcher()
classifier = MatcherClassifier()

for market_a in markets:
    for market_b in markets:
        if market_a.source == market_b.source:
            continue
        
        # Rule-based match
        match = matcher.match_single_pair(market_a, market_b)
        
        if match.match_score < 0.6:
            continue
        
        # Classifier probability
        prob = classifier.predict(market_a, market_b)
        
        # Persist to database
        save_matched_pair(
            session,
            market_a.source, market_a.market_id,
            market_b.source, market_b.market_id,
            similarity=match.match_score,
            classifier_probability=prob,
            name_similarity=match.name_similarity,
            category_similarity=match.category_similarity,
            temporal_proximity=match.temporal_proximity,
        )

session.close()
```

## Data Quality Considerations

### Pair Ordering

The system automatically ensures consistent pair ordering:
- Pairs are stored with `source_a < source_b` (or `market_id_a < market_id_b` if same source)
- This prevents duplicate records when querying in different orders
- Ordering is handled transparently in `save_matched_pair()` and `confirm_matched_pair()`

### Deduplication

- The unique constraint prevents duplicate (source_a, market_id_a, source_b, market_id_b) combinations
- Attempting to save the same pair twice will update the existing record
- Timestamps are automatically updated on modification

### Score Semantics

- **similarity**: Overall match score [0, 1] from rule-based matcher
- **classifier_probability**: ML classifier confidence [0, 1]
- **name_similarity**: Text similarity of market names [0, 1]
- **category_similarity**: Category match score [0, 1]
- **temporal_proximity**: Time alignment score [0, 1]

## Testing

The matched pairs feature includes 12 comprehensive tests:

```bash
# Run only matched pair tests
PYTHONPATH=src python -m pytest tests/test_matched_pairs.py -v

# Or run all tests
PYTHONPATH=src python -m pytest tests/ -v
```

**Test Coverage:**
- Save and update pairs
- Pair ordering consistency
- Manual confirmation
- Query filtering (similarity, source, confirmed_only)
- Result ordering (by similarity descending)
- Timestamp tracking and updates

## Best Practices

1. **Regular Persistence**: Run `persist_matches.py` periodically to keep matches up-to-date
2. **Quality Checks**: Manually confirm important matches before using in trading
3. **Filtering**: Use `min_similarity` to focus on high-confidence matches
4. **Source Validation**: Verify source platform compatibility
5. **Notes**: Add notes to matches for future reference

## Troubleshooting

### No matches found

- Check minimum score is not too high: `--min-score 0.5`
- Verify markets are in database: `python scripts/list_markets.py`
- Check market sources are different (same-source pairs are skipped)

### Duplicate matches appearing

- This shouldn't happen due to unique constraint
- Clear and rebuild: `persist_matches.py --clear`

### Confirmed matches not showing

- Use filter: `view_matches.py --confirmed`
- Check confirmation was saved: confirm returns non-null on success
