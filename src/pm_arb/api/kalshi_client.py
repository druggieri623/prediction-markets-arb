
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import requests

from .models import UnifiedMarket, UnifiedContract

logger = logging.getLogger(__name__)

KALSHI_BASE = "https://api.elections.kalshi.com/trade-api/v2"


class KalshiClient:
    """
    Minimal read-only client for Kalshi market data.

    NOTE: This uses only public GET endpoints (no authentication).
    """

    def __init__(self, base_url: str = KALSHI_BASE, timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    # ------------- HTTP helper -------------

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        resp = requests.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    # ------------- Public methods -------------

    def list_markets(
        self,
        status: str = "open",
        limit: int = 100,
        series_ticker: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch a list of markets.

        status: "open" / "closed" / "all" (depending on Kalshi API support)
        limit:  number of markets to fetch
        """
        params: Dict[str, Any] = {
            "status": status,
            "limit": limit,
        }
        if series_ticker:
            params["series_ticker"] = series_ticker

        data = self._get("/markets", params=params)
        return data.get("markets", [])

    def get_market(self, ticker: str) -> Dict[str, Any]:
        """Fetch a single Kalshi market by ticker."""
        return self._get(f"/markets/{ticker}")

    def get_orderbook(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Fetch orderbook for a ticker.

        Returns a dict with "orderbook" or None on non-200.
        """
        url = f"{self.base_url}/markets/{ticker}/orderbook"
        resp = requests.get(url, timeout=self.timeout)
        if resp.status_code != 200:
            logger.warning("Kalshi orderbook %s returned %s", ticker, resp.status_code)
            return None
        data = resp.json()
        return data.get("orderbook")

    # ------------- Normalization -------------

    @staticmethod
    def _best_bid_ask_from_orderbook(
        book: Dict[str, Any]
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        Extract approximate YES bid/ask prices in probability space [0,1].

        Kalshi orderbook "yes"/"no" are lists of [price_cents, quantity].
        We take:
          - best YES bid = max yes bid
          - approximate YES ask = 1 - best NO bid  (binary complement)
        """
        yes_bids = book.get("yes") or []
        no_bids = book.get("no") or []

        if not yes_bids or not no_bids:
            return None, None

        best_yes_bid_cents = max(b[0] for b in yes_bids)
        best_no_bid_cents = max(b[0] for b in no_bids)

        best_yes_bid = best_yes_bid_cents / 100.0
        best_yes_ask = 1.0 - (best_no_bid_cents / 100.0)

        if not (0.0 <= best_yes_bid <= 1.0):
            best_yes_bid = None
        if not (0.0 <= best_yes_ask <= 1.0):
            best_yes_ask = None

        return best_yes_bid, best_yes_ask

    def normalize_market(
        self,
        raw_market: Dict[str, Any],
        orderbook: Optional[Dict[str, Any]] = None,
    ) -> UnifiedMarket:
        """
        Convert a raw Kalshi market + optional orderbook into a UnifiedMarket.

        For now, we expose a single "YES" UnifiedContract, which is enough
        for implied probability and arbitrage detection; you can later
        add an explicit "NO" contract if you want symmetry.
        """
        ticker = raw_market.get("ticker", "")
        name = raw_market.get("title") or raw_market.get("name") or ticker
        category = raw_market.get("category") or raw_market.get("event_ticker")
        event_time = raw_market.get("expiration_time")

        bid, ask = (None, None)
        if orderbook is not None:
            bid, ask = self._best_bid_ask_from_orderbook(orderbook)

        yes_contract = UnifiedContract(
            source="kalshi",
            market_id=ticker,
            contract_id=f"{ticker}_YES",
            name="YES",
            side="YES",
            outcome_type="binary",
            price_bid=bid,
            price_ask=ask,
            last_price=None,
            volume=None,
            open_interest=None,
            extra={
                "raw_market": raw_market,
                "orderbook": orderbook,
            },
        )

        return UnifiedMarket(
            source="kalshi",
            market_id=ticker,
            name=name,
            event_time=event_time,
            category=category,
            contracts=[yes_contract],
            extra={"raw_market": raw_market},
        )
