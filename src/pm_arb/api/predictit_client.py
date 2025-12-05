from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import requests

from .models import UnifiedMarket, UnifiedContract

logger = logging.getLogger(__name__)

PREDICTIT_ALL = "https://www.predictit.org/api/marketdata/all/"


class PredictItClient:
    """
    Read-only client for PredictIt's public market data API.
    """

    def __init__(self, base_url: str = PREDICTIT_ALL, timeout: int = 10):
        self.base_url = base_url
        self.timeout = timeout

    def _get(self, url: str) -> Dict[str, Any]:
        resp = requests.get(url, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def list_markets(self) -> List[Dict[str, Any]]:
        """
        Fetch all markets. PredictIt returns a top-level 'markets' array.
        """
        data = self._get(self.base_url)
        return data.get("markets", [])

    def get_market(self, market_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch a single market by id by filtering list_markets.
        (PredictIt also has /markets/{id} endpoint, but this keeps the client simple.)
        """
        market_id_str = str(market_id)
        for m in self.list_markets():
            if str(m.get("id")) == market_id_str:
                return m
        return None

    # ------------- Normalization -------------

    @staticmethod
    def _to_prob(val: Any) -> Optional[float]:
        if val is None:
            return None
        try:
            return float(val)
        except (TypeError, ValueError):
            return None

    def normalize_market(self, raw_market: Dict[str, Any]) -> UnifiedMarket:
        """
        Normalize a PredictIt market into a UnifiedMarket.

        PredictIt prices are quoted in dollar terms (0.01 to 0.99)
        and already represent probabilities, so we keep them as-is.
        """
        market_id = str(raw_market.get("id"))
        name = raw_market.get("name") or market_id
        category = raw_market.get("shortName")
        event_time = raw_market.get("timeStamp")

        contracts: List[UnifiedContract] = []

        raw_contracts = raw_market.get("contracts", [])
        outcome_type = "multi" if len(raw_contracts) > 2 else "binary"

        for c in raw_contracts:
            cid = str(c.get("id"))
            label = c.get("name") or cid

            last_trade = self._to_prob(c.get("lastTradePrice"))
            best_buy_yes = self._to_prob(c.get("bestBuyYesCost"))
            best_buy_no = self._to_prob(c.get("bestBuyNoCost"))
            volume = c.get("volume")

            # We treat YES as the main direction; if you want explicit NO contracts,
            # you can add them separately or interpret best_buy_no as 1 - prob.
            contract = UnifiedContract(
                source="predictit",
                market_id=market_id,
                contract_id=cid,
                name=label,
                side=label,
                outcome_type=outcome_type,
                price_bid=best_buy_yes,   # what you can sell shares at (approx)
                price_ask=best_buy_yes,   # simple representation; refine later
                last_price=last_trade,
                volume=volume,
                open_interest=None,
                extra={
                    "best_buy_no": best_buy_no,
                    "raw_contract": c,
                },
            )
            contracts.append(contract)

        return UnifiedMarket(
            source="predictit",
            market_id=market_id,
            name=name,
            event_time=event_time,
            category=category,
            contracts=contracts,
            extra={"raw_market": raw_market},
        )
