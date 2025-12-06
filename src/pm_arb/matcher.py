"""
Market matching layer using machine learning.

This module provides tools to link similar markets across platforms using
scikit-learn's text similarity features (TF-IDF, cosine similarity) combined
with fuzzy string matching and structural analysis.

Key classes:
- MarketMatcher: Main class for finding matches between markets
- MatchResult: Data class representing a potential match
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from difflib import SequenceMatcher

from .api.models import UnifiedMarket, UnifiedContract, SourceType


@dataclass
class MatchResult:
    """Represents a potential match between two markets."""
    market_a: UnifiedMarket
    market_b: UnifiedMarket
    match_score: float  # Overall match score [0, 1]
    
    # Component scores
    name_similarity: float
    category_similarity: float
    contract_similarity: float
    temporal_proximity: float
    
    # Additional details
    matching_contracts: List[Tuple[UnifiedContract, UnifiedContract]] = field(default_factory=list)
    confidence: str = "unknown"  # "high", "medium", "low"
    notes: str = ""
    
    def __repr__(self) -> str:
        return (
            f"Match({self.market_a.source}/{self.market_a.market_id} <-> "
            f"{self.market_b.source}/{self.market_b.market_id}, "
            f"score={self.match_score:.3f}, confidence={self.confidence})"
        )


class MarketMatcher:
    """
    Machine learning-based market matcher that links similar markets across platforms.
    
    Uses:
    - TF-IDF vectorization for market name similarity
    - Cosine similarity for semantic matching
    - Contract structure analysis for cross-platform matching
    - Fuzzy string matching as fallback
    """
    
    def __init__(
        self,
        name_weight: float = 0.4,
        category_weight: float = 0.2,
        contract_weight: float = 0.3,
        temporal_weight: float = 0.1,
        min_score_threshold: float = 0.5,
        max_days_apart: int = 7,
    ):
        """
        Initialize the market matcher.
        
        Args:
            name_weight: Weight for market name similarity [0, 1]
            category_weight: Weight for category match [0, 1]
            contract_weight: Weight for contract structure similarity [0, 1]
            temporal_weight: Weight for temporal proximity [0, 1]
            min_score_threshold: Minimum match score to consider (0-1)
            max_days_apart: Max days between event times for temporal match
        """
        total = name_weight + category_weight + contract_weight + temporal_weight
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total}")
        
        self.name_weight = name_weight
        self.category_weight = category_weight
        self.contract_weight = contract_weight
        self.temporal_weight = temporal_weight
        self.min_score_threshold = min_score_threshold
        self.max_days_apart = max_days_apart
        
        self._vectorizer = TfidfVectorizer(
            analyzer="char",
            ngram_range=(2, 3),
            lowercase=True,
            strip_accents="ascii",
        )
    
    def find_matches(
        self,
        markets_a: List[UnifiedMarket],
        markets_b: Optional[List[UnifiedMarket]] = None,
        cross_source_only: bool = True,
    ) -> List[MatchResult]:
        """
        Find matching markets between two lists.
        
        Args:
            markets_a: First list of markets
            markets_b: Second list of markets (if None, matches within markets_a)
            cross_source_only: Only match markets from different sources
        
        Returns:
            List of MatchResult sorted by match_score (descending)
        """
        if markets_b is None:
            markets_b = markets_a
            within_same_list = True
        else:
            within_same_list = False
        
        matches: List[MatchResult] = []
        
        # Extract market names and build vectorizer
        names_a = [self._clean_text(m.name) for m in markets_a]
        names_b = [self._clean_text(m.name) for m in markets_b]
        all_names = names_a + (names_b if not within_same_list else [])
        
        if not all_names:
            return []
        
        # Fit TF-IDF vectorizer
        tfidf_matrix_all = self._vectorizer.fit_transform(all_names)
        tfidf_matrix_a = tfidf_matrix_all[: len(names_a)]
        tfidf_matrix_b = tfidf_matrix_all[
            len(names_a) : len(names_a) + len(names_b)
        ] if not within_same_list else tfidf_matrix_all[: len(names_b)]
        
        # Compute similarity matrix
        similarity_matrix = cosine_similarity(tfidf_matrix_a, tfidf_matrix_b)
        
        # Find potential matches
        for i, market_a in enumerate(markets_a):
            for j, market_b in enumerate(markets_b):
                # Skip self-matches
                if within_same_list and i >= j:
                    continue
                
                # Skip if different sources not required
                if cross_source_only and market_a.source == market_b.source:
                    continue
                
                # Compute match score
                name_sim = float(similarity_matrix[i, j])
                category_sim = self._compute_category_similarity(market_a, market_b)
                contract_sim = self._compute_contract_similarity(market_a, market_b)
                temporal_sim = self._compute_temporal_similarity(market_a, market_b)
                
                overall_score = (
                    self.name_weight * name_sim
                    + self.category_weight * category_sim
                    + self.contract_weight * contract_sim
                    + self.temporal_weight * temporal_sim
                )
                
                # Filter by threshold
                if overall_score < self.min_score_threshold:
                    continue
                
                # Find matching contracts
                matching_contracts = self._match_contracts(market_a, market_b)
                
                # Compute confidence
                confidence = self._compute_confidence(
                    overall_score,
                    name_sim,
                    len(matching_contracts),
                    max(len(market_a.contracts), len(market_b.contracts)),
                )
                
                match = MatchResult(
                    market_a=market_a,
                    market_b=market_b,
                    match_score=overall_score,
                    name_similarity=name_sim,
                    category_similarity=category_sim,
                    contract_similarity=contract_sim,
                    temporal_proximity=temporal_sim,
                    matching_contracts=matching_contracts,
                    confidence=confidence,
                )
                matches.append(match)
        
        # Sort by match score (descending)
        matches.sort(key=lambda m: m.match_score, reverse=True)
        return matches
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text for matching."""
        # Remove special characters, keep alphanumeric and spaces
        text = re.sub(r"[^\w\s]", " ", text.lower())
        # Collapse multiple spaces
        text = re.sub(r"\s+", " ", text)
        return text.strip()
    
    def _compute_category_similarity(
        self, market_a: UnifiedMarket, market_b: UnifiedMarket
    ) -> float:
        """Compute category similarity between markets."""
        cat_a = market_a.category or ""
        cat_b = market_b.category or ""
        
        if not cat_a or not cat_b:
            return 0.5  # Neutral if either missing
        
        if cat_a.lower() == cat_b.lower():
            return 1.0
        
        # Partial category match (e.g., "Politics" vs "U.S. Politics")
        if cat_a.lower() in cat_b.lower() or cat_b.lower() in cat_a.lower():
            return 0.7
        
        return 0.0
    
    def _compute_contract_similarity(
        self, market_a: UnifiedMarket, market_b: UnifiedMarket
    ) -> float:
        """
        Compute contract structure similarity.
        
        Compares outcome types and number of contracts.
        """
        if not market_a.contracts or not market_b.contracts:
            return 0.0
        
        # Check outcome type match
        types_a = {c.outcome_type for c in market_a.contracts}
        types_b = {c.outcome_type for c in market_b.contracts}
        
        common_types = types_a & types_b
        all_types = types_a | types_b
        
        type_similarity = len(common_types) / len(all_types) if all_types else 0.0
        
        # Check contract count similarity (prefer similar counts)
        count_a = len(market_a.contracts)
        count_b = len(market_b.contracts)
        count_similarity = 1.0 - abs(count_a - count_b) / max(count_a, count_b)
        count_similarity = max(0.0, count_similarity)
        
        return 0.6 * type_similarity + 0.4 * count_similarity
    
    def _match_contracts(
        self, market_a: UnifiedMarket, market_b: UnifiedMarket
    ) -> List[Tuple[UnifiedContract, UnifiedContract]]:
        """Find matching contracts between two markets."""
        matches: List[Tuple[UnifiedContract, UnifiedContract]] = []
        
        for contract_a in market_a.contracts:
            for contract_b in market_b.contracts:
                similarity = self._fuzzy_match(
                    contract_a.name, contract_b.name
                )
                # Consider match if >60% similar and same outcome type
                if (
                    similarity > 0.6
                    and contract_a.outcome_type == contract_b.outcome_type
                ):
                    matches.append((contract_a, contract_b))
        
        return matches
    
    def _compute_temporal_similarity(
        self, market_a: UnifiedMarket, market_b: UnifiedMarket
    ) -> float:
        """
        Compute temporal proximity between markets.
        
        Markets with closer event times are more likely to be the same event.
        """
        if not market_a.event_time or not market_b.event_time:
            return 0.5  # Neutral if either missing
        
        try:
            # Try to parse ISO8601 format
            time_a = self._parse_event_time(market_a.event_time)
            time_b = self._parse_event_time(market_b.event_time)
            
            if not time_a or not time_b:
                return 0.5
            
            days_apart = abs((time_a - time_b).days)
            
            if days_apart == 0:
                return 1.0
            if days_apart <= self.max_days_apart:
                return 1.0 - (days_apart / self.max_days_apart)
            return 0.0
        except Exception:
            return 0.5
    
    def _parse_event_time(self, time_str: str) -> Optional[datetime]:
        """Parse event time from various formats."""
        try:
            # Try ISO8601
            return datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        except ValueError:
            try:
                # Try common formats
                from dateutil import parser
                return parser.parse(time_str)
            except Exception:
                return None
    
    def _fuzzy_match(self, text_a: str, text_b: str) -> float:
        """Compute fuzzy string similarity using SequenceMatcher."""
        text_a = self._clean_text(text_a)
        text_b = self._clean_text(text_b)
        return SequenceMatcher(None, text_a, text_b).ratio()
    
    def _compute_confidence(
        self,
        overall_score: float,
        name_sim: float,
        matching_contract_count: int,
        total_contracts: int,
    ) -> str:
        """
        Compute confidence level for a match.
        
        Returns "high", "medium", or "low".
        """
        # High confidence: high overall score + good name match + contract overlap
        if (
            overall_score > 0.8
            and name_sim > 0.7
            and matching_contract_count > 0
        ):
            return "high"
        
        # Medium confidence: decent score with some contract overlap
        if (
            overall_score > 0.65
            or (overall_score > 0.5 and matching_contract_count > 0)
        ):
            return "medium"
        
        return "low"
    
    def match_single_pair(
        self, market_a: UnifiedMarket, market_b: UnifiedMarket
    ) -> MatchResult:
        """Match a single pair of markets."""
        matches = self.find_matches([market_a], [market_b], cross_source_only=False)
        if matches:
            return matches[0]
        else:
            # Return a low-score non-match
            return MatchResult(
                market_a=market_a,
                market_b=market_b,
                match_score=0.0,
                name_similarity=0.0,
                category_similarity=0.0,
                contract_similarity=0.0,
                temporal_proximity=0.0,
                confidence="low",
                notes="No match found",
            )
