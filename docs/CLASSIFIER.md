# Market Matching Classifier

## Overview

The `MatcherClassifier` is a logistic regression-based machine learning model that predicts the probability that two markets represent the same prediction event across different platforms. It complements the rule-based `MarketMatcher` by learning optimal feature weights from labeled training data.

## Features

### Input Features

The classifier uses three key features extracted from market pairs:

1. **TF-IDF Similarity** (0-1 scale)

   - Fuzzy string matching on market names
   - Higher values indicate more similar names
   - Captures semantic similarity between market descriptions

2. **Time Difference** (in days)

   - Absolute number of days between event resolution times
   - 0 days = same calendar date
   - 365+ days = very different time horizons
   - Serves as a raw feature (classifier learns optimal weighting)

3. **Category Match** (binary: 0 or 1)
   - 1.0 if market categories match exactly
   - 0.0 if categories differ or missing
   - Binary indicator of category alignment

### Output

- **Probability**: Value between 0 and 1 representing the likelihood that two markets represent the same event
- High probability (>0.7): Likely the same market
- Medium probability (0.3-0.7): Uncertain, may warrant manual review
- Low probability (<0.3): Likely different markets

## Model Architecture

```
Input Features (3)
    ↓
StandardScaler (normalize features)
    ↓
LogisticRegression (binary classification)
    ↓
Sigmoid function
    ↓
Output Probability [0, 1]
```

## Feature Importance

Based on training on sample data:

| Feature        | Importance |
| -------------- | ---------- |
| time_diff      | 45.1%      |
| category_match | 36.4%      |
| tfidf_sim      | 18.5%      |

**Interpretation**: Time difference is the strongest predictor, followed by category match. TF-IDF similarity alone is a weaker signal, likely because it captures more semantic variation across platforms.

## Model Performance

On the sample training set:

- **Accuracy**: 78.57%
- **AUC-ROC**: 0.8485
- **Training samples**: 14 pairs (3 positive, 11 negative)

## Usage

### Basic Usage

```python
from pm_arb.matcher_classifier import MatcherClassifier
from pm_arb.sql_storage import init_db, load_market

# Initialize classifier
classifier = MatcherClassifier()

# Load some markets
engine, SessionLocal = init_db("sqlite:///pm_arb_demo.db")
session = SessionLocal()

# ... load market_a and market_b ...

# Make a prediction
probability = classifier.predict(market_a, market_b)
print(f"Probability of match: {probability:.2%}")
```

### Training on Custom Data

```python
# Create training data (lists of positive and negative market pairs)
positive_pairs = [
    (bitcoin_kalshi, bitcoin_polymarket),
    (inflation_kalshi, inflation_predictit),
    # ... more known matches ...
]

negative_pairs = [
    (bitcoin, inflation),
    (bitcoin, agi),
    # ... more known non-matches ...
]

# Train the model
metrics = classifier.train(positive_pairs, negative_pairs)

print(f"Accuracy: {metrics['accuracy']:.2%}")
print(f"AUC-ROC: {metrics['auc_roc']:.4f}")
```

### Batch Predictions

```python
# Make predictions on multiple pairs at once
markets = [market_a, market_b, market_c]
probabilities = []

for i, m_a in enumerate(markets):
    for m_b in markets[i+1:]:
        prob = classifier.predict(m_a, m_b)
        probabilities.append(prob)

# Or use predict_batch for efficiency
pairs = [(m_a, m_b), (m_c, m_d)]
probs = classifier.predict_batch(pairs)
```

### Model Serialization

```python
# Save trained model
classifier.save('classifier_model.pkl')

# Load trained model
classifier = MatcherClassifier()
classifier.load('classifier_model.pkl')
```

### Feature Importance

```python
# Get relative importance of each feature
importance = classifier.get_feature_importance()
# Returns: {'tfidf_sim': 0.1847, 'time_diff': 0.4513, 'category_match': 0.3640}

for feature, score in sorted(importance.items(), key=lambda x: x[1], reverse=True):
    print(f"{feature}: {score*100:.1f}%")
```

## Comparison with Rule-Based Matcher

### Rule-Based Matcher (MarketMatcher)

- ✅ Fast, no training required
- ✅ Interpretable component scores
- ✅ Good default weights for most cases
- ❌ Fixed weights may not generalize well
- ❌ No probabilistic confidence measure

### ML Classifier (MatcherClassifier)

- ✅ Learns optimal feature weights from data
- ✅ Probabilistic output (confidence measures)
- ✅ Better generalization with more training data
- ❌ Requires labeled training data
- ❌ Slightly slower due to ML inference
- ❌ Less interpretable ("black box")

### Combined Approach

For best results, use both:

1. **Rule-based matcher** for initial screening (fast, many candidates)
2. **ML classifier** for ranking and confidence assessment
3. **Manual review** for borderline cases (0.3-0.7 probability range)

## Demo Scripts

### Train and Evaluate Classifier

```bash
python scripts/train_classifier.py --db pm_arb_demo.db
```

Shows:

- Training data composition
- Model metrics (accuracy, AUC-ROC, coefficients)
- Feature importance breakdown
- Example predictions on test pairs

### Find Matches with Classifier

```bash
python scripts/match_with_classifier.py --db pm_arb_demo.db --threshold 0.5
```

Shows:

- Markets loaded from database
- Classifier training summary
- Detected matches above probability threshold
- Side-by-side comparison with rule-based scorer

## Implementation Details

### Feature Extraction

```python
def extract_features(market_a, market_b):
    # 1. TF-IDF similarity via fuzzy matching
    tfidf_sim = self._fuzzy_match(market_a.name, market_b.name)

    # 2. Time difference in days
    time_diff = self._compute_time_diff(market_a, market_b)

    # 3. Category exact match
    category_match = self._compute_category_match(market_a, market_b)

    return np.array([[tfidf_sim, time_diff, category_match]])
```

### Training Process

1. Extract features from all positive pairs
2. Extract features from all negative pairs
3. Normalize features with StandardScaler (critical for logistic regression)
4. Fit LogisticRegression model
5. Calculate performance metrics (accuracy, AUC-ROC)

### Prediction Process

1. Extract features from query pair
2. Scale features using the same scaler from training
3. Call model.predict_proba() to get probability
4. Return probability for "same market" class

## Limitations

1. **Training Data Quality**: Model performance depends on having accurate labeled pairs
2. **Limited Feature Set**: Only uses 3 features; more features (e.g., price, volume, user count) could improve performance
3. **Class Imbalance**: Sample data has many more negative pairs than positive (3:11 ratio)
4. **Temporal Issues**: Markets with missing or ambiguous event times get penalty (365 days)
5. **Generalization**: Model trained on specific platforms/categories may not generalize to new markets

## Potential Improvements

### Short Term

- [ ] Cross-validation with stratified folds
- [ ] ROC curve visualization
- [ ] Confusion matrix analysis
- [ ] Threshold optimization for precision/recall tradeoff
- [ ] Handle class imbalance with SMOTE or class weights

### Medium Term

- [ ] Add more features:
  - Current market price/odds
  - Market volume and liquidity
  - Number of participants
  - Historical accuracy of platform
  - Linguistic similarity (word embeddings)

### Long Term

- [ ] Use more sophisticated models (Random Forest, Gradient Boosting, Neural Networks)
- [ ] Multi-class classification (same event, different event, uncertain)
- [ ] Online learning to adapt to new platforms and market types
- [ ] Explainable AI techniques (SHAP values) for interpretability

## Testing

The classifier includes comprehensive unit tests:

```bash
PYTHONPATH=src python -m pytest tests/test_matcher_classifier.py -v
```

**Test Coverage** (16 tests):

- Initialization and configuration
- Feature extraction (TF-IDF, time difference, category match)
- Training on various data distributions
- Prediction (single and batch)
- Feature importance calculation
- Model serialization (save/load)

All tests passing ✓

## Integration with Arbitrage System

The classifier can be integrated into the full arbitrage detection pipeline:

```
1. Raw Markets (multiple platforms)
    ↓
2. Market Matcher (rule-based, fast)
    ↓
3. Candidate Matches (100s of candidates)
    ↓
4. MatcherClassifier (ML ranking)
    ↓
5. Ranked Matches (sorted by probability)
    ↓
6. Arbitrage Detector (find profitable pairs)
    ↓
7. Trading Signals
```

## References

- **Logistic Regression**: https://scikit-learn.org/stable/modules/linear_model.html#logistic-regression
- **Feature Scaling**: https://scikit-learn.org/stable/modules/preprocessing.html#standardization
- **ROC-AUC Metrics**: https://scikit-learn.org/stable/modules/model_evaluation.html#roc-metrics

## License

Same as parent project (PM ARB)
