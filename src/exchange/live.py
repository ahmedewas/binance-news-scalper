"""Live Binance Spot Exchange implementation via CCXT."""
import logging
from typing import List, Dict, Any
import ccxt
from src.exchange.base import BaseExchange
from src.core.models import OrderResult

logger = logging.getLogger("LiveExchange")


class LiveExchange(BaseExchange):
    def __init__(self, api_key: str, api_secret: str):
        self.client = ccxt.binance({
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
            "options": {"defaultType": "spot"},
        })
        self._price_cache: Dict[str, float] = {}

    def get_balance(self, asset: str = "USDT") -> float:
        try:
            bal = self.client.fetch_balance()
            return float(bal.get(asset, {}).get("free", 0.0))
        except Exception as e:
            logger.error(f"Error fetching balance for {asset}: {e}")
            return 0.0

    def get_ticker_price(self, symbol: str) -> float:
        try:
            ticker = self.client.fetch_ticker(symbol)
            p = float(ticker.get("last", 0.0))
            if p > 0:
                self._price_cache[symbol] = p
            return p or self._price_cache.get(symbol, 0.0)
        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol}: {e}")
            return self._price_cache.get(symbol, 0.0)

    def get_historical_klines(
        self, symbol: str, timeframe: str = "1m", limit: int = 50
    ) -> List[Dict[str, Any]]:
        try:
            raw = self.client.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            return [
                {
                    "open": float(c[1]),
                    "high": float(c[2]),
                    "low": float(c[3]),
                    "close": float(c[4]),
                    "volume": float(c[5]),
                }
                for c in raw
            ]
        except Exception as e:
            logger.error(f"Error fetching klines for {symbol}: {e}")
            return []

    def place_market_buy(self, symbol: str, cost_usdt: float) -> OrderResult:
        try:
            order = self.client.create_order(
                symbol, "market", "buy", None, None, {"quoteOrderQty": cost_usdt}
            )
            price = float(order.get("average") or order.get("price") or 0.0)
            amount = float(order.get("filled") or order.get("amount") or 0.0)
            return OrderResult(
                True, str(order["id"]), symbol, price, amount, "BUY", "FILLED", "Live Buy"
            )
        except Exception as e:
            logger.error(f"Failed live market buy {symbol}: {e}")
            return OrderResult(False, "", symbol, 0.0, 0.0, "BUY", "FAILED", str(e))

    def place_market_sell(self, symbol: str, amount: float) -> OrderResult:
        try:
            qty = float(self.client.amount_to_precision(symbol, amount)) if hasattr(self.client, "amount_to_precision") else amount
            order = self.client.create_market_sell_order(symbol, qty)
            price = float(order.get("average") or order.get("price") or 0.0)
            filled = float(order.get("filled") or amount)
            return OrderResult(
                True, str(order["id"]), symbol, price, filled, "SELL", "FILLED", "Live Sell"
            )
        except Exception as e:
            logger.error(f"Failed live market sell {symbol}: {e}")
            return OrderResult(False, "", symbol, 0.0, 0.0, "SELL", "FAILED", str(e))
