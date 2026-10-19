"""Simulated Paper Exchange using live market prices without real funds."""
import time
import requests
from typing import List, Dict, Any
from src.exchange.base import BaseExchange
from src.core.models import OrderResult


class PaperExchange(BaseExchange):
    def __init__(self, initial_usdt: float = 15.0):
        self.usdt_balance = float(initial_usdt)
        self.holdings: Dict[str, float] = {}
        self.fee_rate = 0.001  # 0.1% spot fee
        self._price_cache: Dict[str, float] = {}
        self.session = requests.Session()

    def get_balance(self, asset: str = "USDT") -> float:
        if asset == "USDT":
            return round(self.usdt_balance, 4)
        return round(self.holdings.get(asset, 0.0), 6)

    def get_ticker_price(self, symbol: str) -> float:
        clean = symbol.replace("/", "").upper()
        try:
            r = self.session.get(
                f"https://api.binance.com/api/v3/ticker/price?symbol={clean}",
                timeout=3,
            )
            if r.status_code == 200:
                p = float(r.json()["price"])
                self._price_cache[clean] = p
                return p
        except Exception:
            pass
        return self._price_cache.get(clean, 0.0)

    def get_historical_klines(
        self, symbol: str, timeframe: str = "1m", limit: int = 50
    ) -> List[Dict[str, Any]]:
        clean = symbol.replace("/", "").upper()
        try:
            url = f"https://api.binance.com/api/v3/klines?symbol={clean}&interval={timeframe}&limit={limit}"
            r = self.session.get(url, timeout=4)
            if r.status_code == 200:
                return [
                    {
                        "open": float(k[1]),
                        "high": float(k[2]),
                        "low": float(k[3]),
                        "close": float(k[4]),
                        "volume": float(k[5]),
                    }
                    for k in r.json()
                ]
        except Exception:
            pass
        return []

    def place_market_buy(self, symbol: str, cost_usdt: float) -> OrderResult:
        if cost_usdt > self.usdt_balance:
            return OrderResult(False, "", symbol, 0.0, 0.0, "BUY", "REJECTED", "Insufficient USDT")

        price = self.get_ticker_price(symbol)
        if price <= 0:
            return OrderResult(False, "", symbol, 0.0, 0.0, "BUY", "FAILED", "Invalid price")

        fee = cost_usdt * self.fee_rate
        net_cost = cost_usdt - fee
        amount = net_cost / price
        self.usdt_balance -= cost_usdt
        base = symbol.split("/")[0] if "/" in symbol else symbol.replace("USDT", "")
        self.holdings[base] = self.holdings.get(base, 0.0) + amount

        order_id = f"paper_buy_{int(time.time()*1000)}"
        return OrderResult(True, order_id, symbol, price, amount, "BUY", "FILLED", "Simulated Buy")

    def place_market_sell(self, symbol: str, amount: float) -> OrderResult:
        base = symbol.split("/")[0] if "/" in symbol else symbol.replace("USDT", "")
        avail = self.holdings.get(base, 0.0)
        if amount > avail * 1.0001:
            return OrderResult(False, "", symbol, 0.0, 0.0, "SELL", "REJECTED", "Insufficient asset")

        price = self.get_ticker_price(symbol)
        gross = amount * price
        fee = gross * self.fee_rate
        net_usdt = gross - fee
        self.holdings[base] = max(0.0, avail - amount)
        self.usdt_balance += net_usdt

        order_id = f"paper_sell_{int(time.time()*1000)}"
        return OrderResult(True, order_id, symbol, price, amount, "SELL", "FILLED", "Simulated Sell")
