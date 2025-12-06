"""
Logistic regression classifier for market matching.

This module provides a trainable classifier that predicts the probability
that two markets are truly the same based on three key features:
- TF-IDF similarity of market names
- Temporal difference (days apart)
- Category equality flag (1 if exact match, 0 otherwise)

The classifier learns from labeled market pairs to optimize match probability.
"""

from __future__ import annotations

import pickle
from datetime import datetime
from typing import List, Optional, Tuple

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, roc_auc_score, roc_curve

from .api.models import UnifiedMarket
from .matcher import MarketMatcher, MatchResult


class MatcherClassifier:
    """
    Logistic regression classifier for market matching probability.
    
    Uses three features:
    1. TF-IDF similarity (0-1): Text similarity of market names
    2. Time difference (int): Days between event dates (-∞ to ∞)
    3. Category match (0-1): 1 if categories match exactly, 0 otherwise
    
    Outputs probability [0, 1] that two markets are truly the same.
    """

    def __init__(self, random_state: int = 42):
        """
        Initialize the classifier.
        
        Args:
            random_state: Random seed for reproducibility
        """
        self.model = LogisticRegression(
            random_state=random_state,
            max_iter=1000,
            solver="lbfgs",
        )
        self.scaler = StandardScaler()
        self.is_fitted = False
        self.matcher = MarketMatcher()  # For feature extraction

    def extract_features(
        self, market_a: UnifiedMarket, market_b: UnifiedMarket
    ) -> np.ndarray:
        """
        Extract features from a pair of markets.
        
        Args:
            market_a: First market
            market_b: Second market
        
        Returns:
            Feature vector [tfidf_sim, time_diff, category_match]
        """
        # Feature 1: TF-IDF similarity
        tfidf_sim = self.matcher._fuzzy_match(market_a.name, market_b.name)
        
        # Feature 2: Time difference in days
        time_diff = self._compute_time_diff(market_a, market_b)
        
        # Feature 3: Category equality flag
        category_match = self._compute_category_match(market_a, market_b)
        
        return np.array([[tfidf_sim, time_diff, category_match]])

    def _compute_time_diff(
        self, market_a: UnifiedMarket, market_b: UnifiedMarket
    ) -> float:
        """Compute time difference in days between markets."""
        if not market_a.event_time or not market_b.event_time:
            return 365  # Large penalty for missing dates

        try:
            time_a = self.matcher._parse_event_time(market_a.event_time)
            time_b = self.matcher._parse_event_time(market_b.event_time)

            if not time_a or not time_b:
                return 365

            # Use date() to get just the date part, then compute difference
            date_a = time_a.date()
            date_b = time_b.date()
            return float(abs((date_a - date_b).days))
        except Exception:
            return 365

    def _compute_category_match(
        self, market_a: UnifiedMarket, market_b: UnifiedMarket
    ) -> float:
        """Return 1.0 if categories match exactly, 0.0 otherwise."""
        cat_a = (market_a.category or "").lower()
        cat_b = (market_b.category or "").lower()

        if not cat_a or not cat_b:
            return 0.0

        return 1.0 if cat_a == cat_b else 0.0

    def train(
        self,
        positive_pairs: List[Tuple[UnifiedMarket, UnifiedMarket]],
        negative_pairs: List[Tuple[UnifiedMarket, UnifiedMarket]],
    ) -> dict:
        """
        Train the classifier on labeled market pairs.
        
        Args:
            positive_pairs: List of (market_a, market_b) tuples that are truly the same
            negative_pairs: List of (market_a, market_b) tuples that are different
        
        Returns:
            Dictionary with training metrics
        """
        # Extract features from positive pairs
        positive_features = np.vstack([
            self.extract_features(a, b) for a, b in positive_pairs
        ])
        positive_labels = np.ones(len(positive_pairs))

        # Extract features from negative pairs
        negative_features = np.vstack([
            self.extract_features(a, b) for a, b in negative_pairs
        ])
        negative_labels = np.zeros(len(negative_pairs))

        # Combine and shuffle
        X = np.vstack([positive_features, negative_features])
        y = np.concatenate([positive_labels, negative_labels])

        # Fit scaler and scale features
        X_scaled = self.scaler.fit_transform(X)

        # Train logistic regression
        self.model.fit(X_scaled, y)
        self.is_fitted = True

        # Compute metrics
        y_pred = self.model.predict(X_scaled)
        y_pred_proba = self.model.predict_proba(X_scaled)[:, 1]

        metrics = {
            "n_positive": len(positive_pairs),
            "n_negative": len(negative_pairs),
            "n_total": len(X),
            "accuracy": float(np.mean(y_pred == y)),
            "auc_roc": float(roc_auc_score(y, y_pred_proba)),
            "coefficients": dict(
                zip(
                    ["tfidf_sim", "time_diff", "category_match"],
                    self.model.coef_[0],
                )
            ),
            "intercept": float(self.model.intercept_[0]),
        }

        return metrics

    def predict(self, market_a: UnifiedMarket, market_b: UnifiedMarket) -> float:
        """
        Predict probability that two markets are the same.
        
        Args:
            market_a: First market
            market_b: Second market
        
        Returns:
            Probability [0, 1] that markets are the same
        """
        if not self.is_fitted:
            raise ValueError(
                "Classifier must be trained before making predictions. "
                "Call train() first."
            )

        features = self.extract_features(market_a, market_b)
        features_scaled = self.scaler.transform(features)
        return float(self.model.predict_proba(features_scaled)[0, 1])

    def predict_batch(
        self, market_pairs: List[Tuple[UnifiedMarket, UnifiedMarket]]
    ) -> List[float]:
        """
        Predict probabilities for multiple market pairs.
        
        Args:
            market_pairs: List of (market_a, market_b) tuples
        
        Returns:
            List of probabilities
        """
        return [self.predict(a, b) for a, b in market_pairs]

    def save(self, filepath: str) -> None:
        """Save the trained classifier to a file."""
        if not self.is_fitted:
            raise ValueError("Cannot save unfitted classifier")

        data = {
            "model": self.model,
            "scaler": self.scaler,
            "is_fitted": self.is_fitted,
        }

        with open(filepath, "wb") as f:
            pickle.dump(data, f)

    def load(self, filepath: str) -> None:
        """Load a trained classifier from a file."""
        with open(filepath, "rb") as f:
            data = pickle.load(f)

        self.model = data["model"]
        self.scaler = data["scaler"]
        self.is_fitted = data["is_fitted"]

    def get_feature_importance(self) -> dict:
        """
        Get relative importance of features based on coefficients.
        
        Returns:
            Dictionary with feature names and their importance scores
        """
        if not self.is_fitted:
            raise ValueError("Classifier must be trained first")

        coefs = np.abs(self.model.coef_[0])
        total = coefs.sum()

        return {
            "tfidf_sim": float(coefs[0] / total),
            "time_diff": float(coefs[1] / total),
            "category_match": float(coefs[2] / total),
        }
