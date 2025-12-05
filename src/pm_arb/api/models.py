
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Literal


SourceType = Literal["kalshi", "polymarket", "predictit"]


@dataclass
class UnifiedContract:
    """
    A unified representation of a single contract / outcome across all platforms.

    Prices are expressed as probabilities in [0, 1].
    """
    source: SourceType
    market_id: str
    contract_id: str

    name: str               # e.g. "YES", "NO", "Biden", "Lakers", etc.
    side: str               # usually same as name; can be "YES"/"NO" or outcome label
    outcome_type: str       # "binary" | "multi"

    price_bid: Optional[float] = None   # best bid  (what you can sell at)
    price_ask: Optional[float] = None   # best ask  (what you can buy at)
    last_price: Optional[float] = None  # last traded price
    volume: Optional[float] = None      # 24h or lifetime volume if available
    open_interest: Optional[float] = None

    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UnifiedMarket:
    """
    A unified representation of a market (question / event) across platforms.
    """
    source: SourceType
    market_id: str

    name: str
    event_time: Optional[str] = None    # ISO8601 or platform-specific string
    category: Optional[str] = None      # e.g. "Politics", "Sports", "Economy"

    contracts: List[UnifiedContract] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)
