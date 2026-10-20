"""Live Binance Spot Exchange implementation via CCXT."""
import logging
import math
import time
from typing import List, Dict, Any
import ccxt
from src.exchange.base import BaseExchange
from src.exchange.live_orders import LiveOrderMixin
from src.core.models import OrderResult

logger = logging.getLogger("LiveExchange")


class LiveExchange(LiveOrderMixin, BaseExchange):
    def __init__(self, api_key: str, api_secret: str):
        self.client = ccxt.binance({
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
            "timeout": 10000,
            "options": {"defaultType": "spot"},
        })
        self._price_cache: Dict[str, float] = {}

    def get_balance(self, asset: str = "USDT") -> float:
        try:
            bal = self.client.fetch_balance()
            return float(bal.get(asset, {}).get("free", 0.0))
        except Exception as e:
            logger.error("Balance unavailable for %s: %s", asset, type(e).__name__)
            raise RuntimeError("Balance unavailable") from e

    def get_ticker_price(self, symbol: str) -> float:
        try:
            ticker = self.client.fetch_ticker(symbol)
            p = float(ticker.get("last", 0.0))
            if p > 0:
                self._price_cache[symbol] = p
            stamp = ticker.get("timestamp")
            if not math.isfinite(p) or p <= 0 or (stamp and time.time() * 1000 - stamp > 30000):
                return 0.0
            return p
        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol}: {e}")
            return 0.0

    def get_historical_klines(
        self, symbol: str, timeframe: str = "1m", limit: int = 50
    ) -> List[Dict[str, Any]]:
        try:
            raw = self.client.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit + 1)
            duration = self.client.parse_timeframe(timeframe) * 1000
            now_ms = time.time() * 1000
            return [
                {
                    "timestamp": int(c[0]),
                    "close_time": int(c[0] + duration),
                    "open": float(c[1]),
                    "high": float(c[2]),
                    "low": float(c[3]),
                    "close": float(c[4]),
                    "volume": float(c[5]),
                }
                for c in raw if c[0] + duration <= now_ms
            ][-limit:]
        except Exception as e:
            logger.error(f"Error fetching klines for {symbol}: {e}")
            return []

    def get_market_rules(self, symbol: str) -> Dict[str, Any]:
        self.client.load_markets()
        market = self.client.market(symbol)
        limits = market.get("limits") or {}
        return {
            "min_notional": float((limits.get("cost") or {}).get("min") or 0),
            "min_amount": float((limits.get("amount") or {}).get("min") or 0),
            "precision": market.get("precision") or {},
        }

    def normalize_amount(self, symbol: str, amount: float) -> float:
        return float(self.client.amount_to_precision(symbol, amount))

    def place_market_buy(self, symbol: str, cost_usdt: float, client_order_id=None) -> OrderResult:
        return self._submit(symbol, "BUY", cost_usdt, client_order_id)

    def place_market_sell(self, symbol: str, amount: float, client_order_id=None) -> OrderResult:
        return self._submit(symbol, "SELL", amount, client_order_id)
