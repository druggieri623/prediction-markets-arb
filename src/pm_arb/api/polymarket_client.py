from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import requests

from .models import UnifiedMarket, UnifiedContract

logger = logging.getLogger(__name__)

POLY_GAMMA_BASE = "https://gamma-api.polymarket.com"


class PolymarketClient:
    """
    Read-only client for Polymarket Gamma API (markets metadata + mid prices).

    This uses /markets from Gamma; you can later extend this with CLOB/book
    endpoints if you want true orderbook bids/asks.
    """

    def __init__(self, base_url: str = POLY_GAMMA_BASE, timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.base_url}{path}"
        resp = requests.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    # ------------- Public methods -------------

    def list_markets(
        self,
        closed: bool = False,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        """
        Fetch a list of markets from Polymarket Gamma.

        closed=False to fetch open markets.
        """
        params = {"closed": str(closed).lower(), "limit": limit}
        data = self._get("/markets", params=params)
        # Gamma returns a list of market dicts
        if isinstance(data, list):
            return data
        return []

    def get_market(self, market_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a single market by id or slug if the API supports that endpoint.
        Here we do a simple filter over list_markets for demo purposes.
        """
        markets = self.list_markets(closed=False, limit=500)
        for m in markets:
            if m.get("id") == market_id or m.get("slug") == market_id:
                return m
        return None

    # ------------- Normalization -------------

    @staticmethod
    def normalize_market(raw_market: Dict[str, Any]) -> UnifiedMarket:
        """
        Normalize a Polymarket Gamma market into UnifiedMarket.

        Assumes 'outcomes' + 'outcomePrices' correspond to outcomes and their
        AMM mid prices in probability space (0..1).
        """
        market_id = raw_market.get("slug") or raw_market.get("id") or "unknown"
        name = raw_market.get("question") or str(market_id)
        category = raw_market.get("category") or raw_market.get("collection")
        event_time = raw_market.get("endDate") or raw_market.get("closesAt")

        outcomes = raw_market.get("outcomes") or []
        prices = raw_market.get("outcomePrices") or []

        contracts: List[UnifiedContract] = []
        outcome_type = "binary" if len(outcomes) == 2 else "multi"

        for outcome_label, price in zip(outcomes, prices):
            try:
                prob = float(price)
            except (TypeError, ValueError):
                prob = None

            contract = UnifiedContract(
                source="polymarket",
                market_id=market_id,
                contract_id=f"{market_id}_{outcome_label}",
                name=str(outcome_label),
                side=str(outcome_label),
                outcome_type=outcome_type,
                price_bid=None,
                price_ask=prob,
                last_price=prob,
                volume=None,
                open_interest=None,
                extra={},
            )
            contracts.append(contract)

        return UnifiedMarket(
            source="polymarket",
            market_id=market_id,
            name=name,
            event_time=event_time,
            category=category,
            contracts=contracts,
            extra={"raw_market": raw_market},
        )
