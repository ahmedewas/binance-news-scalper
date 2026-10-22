"""Simulated Paper Exchange using live market prices without real funds."""
import time
import math
import requests
from typing import List, Dict, Any
from src.exchange.base import BaseExchange
from src.core.models import OrderResult


class PaperExchange(BaseExchange):
    def __init__(self, initial_usdt: float = 15.0):
        self.usdt_balance = float(initial_usdt)
        self.holdings: Dict[str, float] = {}
        self.fee_rate = 0.001
        self._price_cache: Dict[str, float] = {}
        self.session = requests.Session()

    def get_balance(self, asset: str = "USDT") -> float:
        return round(self.usdt_balance, 4) if asset == "USDT" else round(self.holdings.get(asset, 0.0), 6)

    def get_ticker_price(self, symbol: str) -> float:
        clean = symbol.replace("/", "").upper()
        try:
            r = self.session.get(f"https://api.binance.com/api/v3/ticker/price?symbol={clean}", timeout=3)
            if r.status_code == 200:
                p = float(r.json()["price"])
                if math.isfinite(p) and p > 0:
                    self._price_cache[clean] = p
                    return p
        except Exception:
            pass
        return self._price_cache.get(clean, 0.0)

    def get_historical_klines(self, symbol: str, timeframe: str = "1m", limit: int = 50) -> List[Dict[str, Any]]:
        clean = symbol.replace("/", "").upper()
        try:
            url = f"https://api.binance.com/api/v3/klines?symbol={clean}&interval={timeframe}&limit={limit + 1}"
            r = self.session.get(url, timeout=4)
            if r.status_code == 200:
                return [{"timestamp": int(k[0]), "close_time": int(k[6]), "open": float(k[1]), "high": float(k[2]),
                         "low": float(k[3]), "close": float(k[4]), "volume": float(k[5])}
                        for k in r.json() if int(k[6]) <= time.time() * 1000][-limit:]
        except Exception:
            pass
        return []

    def get_market_rules(self, symbol: str) -> Dict[str, Any]:
        return {"min_notional": 5.0, "min_amount": 0.0}

    def place_market_buy(self, symbol: str, cost_usdt: float, client_order_id=None) -> OrderResult:
        if not math.isfinite(cost_usdt) or cost_usdt <= 0:
            return OrderResult(False, "", symbol, 0, 0, "BUY", "REJECTED", "Invalid quantity")
        if cost_usdt > self.usdt_balance:
            return OrderResult(False, "", symbol, 0.0, 0.0, "BUY", "REJECTED", "Insufficient USDT")
        price = self.get_ticker_price(symbol)
        if not math.isfinite(price) or price <= 0:
            return OrderResult(False, "", symbol, 0.0, 0.0, "BUY", "FAILED", "Invalid price")
        fee = cost_usdt * self.fee_rate
        amount = (cost_usdt - fee) / price
        self.usdt_balance -= cost_usdt
        base = symbol.split("/")[0] if "/" in symbol else symbol.replace("USDT", "")
        self.holdings[base] = self.holdings.get(base, 0.0) + amount
        order_id = client_order_id or f"paper_buy_{time.time_ns()}"
        return OrderResult(True, order_id, symbol, price, amount, "BUY", "FILLED", "Simulated Buy",
                           cost=cost_usdt, fee_base=fee / price, client_order_id=client_order_id or "")

    def place_market_sell(self, symbol: str, amount: float, client_order_id=None) -> OrderResult:
        if not math.isfinite(amount) or amount <= 0:
            return OrderResult(False, "", symbol, 0, 0, "SELL", "REJECTED", "Invalid quantity")
        base = symbol.split("/")[0] if "/" in symbol else symbol.replace("USDT", "")
        avail = self.holdings.get(base, 0.0)
        if amount > avail + 1e-12:
            return OrderResult(False, "", symbol, 0.0, 0.0, "SELL", "REJECTED", "Insufficient asset")
        price = self.get_ticker_price(symbol)
        if not math.isfinite(price) or price <= 0:
            return OrderResult(False, "", symbol, 0, 0, "SELL", "REJECTED", "Invalid price")
        gross = amount * price
        fee = gross * self.fee_rate
        self.holdings[base] = max(0.0, avail - amount)
        self.usdt_balance += (gross - fee)
        order_id = client_order_id or f"paper_sell_{time.time_ns()}"
        return OrderResult(True, order_id, symbol, price, amount, "SELL", "FILLED", "Simulated Sell",
                           cost=gross, fee_quote=fee, client_order_id=client_order_id or "")

    def reconcile_order(self, symbol: str, client_order_id: str) -> OrderResult:
        base = symbol.split("/")[0] if "/" in symbol else symbol.replace("USDT", "")
        avail = self.holdings.get(base, 0.0)
        if avail > 0:
            return self.place_market_sell(symbol, avail, client_order_id)
        return OrderResult(True, client_order_id, symbol, 0, 0, "", "REJECTED",
                           "No holdings for paper reconcile", client_order_id=client_order_id)
