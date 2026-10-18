"""Abstract Base Exchange interface."""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from src.core.models import OrderResult


class BaseExchange(ABC):
    @abstractmethod
    def get_balance(self, asset: str = "USDT") -> float:
        """Fetch liquid asset balance."""
        pass

    @abstractmethod
    def get_ticker_price(self, symbol: str) -> float:
        """Fetch real-time ticker price for a pair."""
        pass

    @abstractmethod
    def get_historical_klines(
        self, symbol: str, timeframe: str = "1m", limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Fetch historical candlestick bars."""
        pass

    @abstractmethod
    def place_market_buy(self, symbol: str, cost_usdt: float) -> OrderResult:
        """Place market buy order specified in quote currency (USDT)."""
        pass

    @abstractmethod
    def place_market_sell(self, symbol: str, amount: float) -> OrderResult:
        """Place market sell order specified in base currency."""
        pass
