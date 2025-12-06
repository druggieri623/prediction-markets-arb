# prediction-markets-arb

Small Python project providing helpers and API utilities for exploring
arbitrage opportunities across prediction markets.

## Key Features

- **Market Matching Engine**: ML-based matching using TF-IDF similarity, fuzzy matching, category alignment, and temporal proximity
- **Logistic Regression Classifier**: Learns optimal weights from labeled data for probabilistic match prediction
- **Matched Pairs Persistence**: Store and manage matched market pairs in SQLite database with manual confirmation
- **Arbitrage Detection**: Find profitable opportunities across markets
- **Multi-Platform Support**: Works with Kalshi, PolyMarket, PredictIt, and other platforms
- **Comprehensive Testing**: 54 unit tests covering matcher, classifier, persistence, and storage

## Getting started

1. Create and activate a virtual environment (recommended):

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Quick Examples

### Find matching markets across platforms
```bash
python scripts/match_markets.py --db pm_arb_demo.db
```

### Train and evaluate the ML classifier
```bash
python scripts/train_classifier.py --db pm_arb_demo.db
```

### Find matches with classifier predictions
```bash
python scripts/match_with_classifier.py --db pm_arb_demo.db --threshold 0.5
```

### Persist matched pairs to database
```bash
python scripts/persist_matches.py --db pm_arb_demo.db --min-score 0.6
```

### View persisted matched pairs
```bash
python scripts/view_matches.py --db pm_arb_demo.db --min-score 0.70
```

## Documentation

- **[MATCHING.md](docs/MATCHING.md)** - Market matcher design and usage
- **[CLASSIFIER.md](docs/CLASSIFIER.md)** - ML classifier guide and examples
- **[MATCHED_PAIRS.md](docs/MATCHED_PAIRS.md)** - Database persistence and management
- **[CLASSIFIER_SUMMARY.md](CLASSIFIER_SUMMARY.md)** - Implementation summary

## Development

- Run the test suite:

```bash
pytest
```

- Run specific tests:

```bash
PYTHONPATH=src python -m pytest tests/test_matcher.py -v
PYTHONPATH=src python -m pytest tests/test_matcher_classifier.py -v
```

- Project code lives under `src/pm_arb`.

## Git

- The repository remote can be HTTPS or SSH. Example HTTPS remote:

```
https://github.com/druggieri623/prediction-markets-arb.git
```

## Contributing

Pull requests are welcome. Please open issues for bugs or feature requests.

## License

See the project license if included. If none, contact the maintainer.
