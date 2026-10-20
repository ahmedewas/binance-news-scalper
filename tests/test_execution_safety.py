"""Offline execution regression tests for live exchange client."""
from types import SimpleNamespace
import pytest
import ccxt
from src.exchange.live import LiveExchange


def live_client(order=None, error=None):
    exchange = LiveExchange("", "")
    def submit(*args, **kwargs):
        if error:
            raise error
        return order
    exchange.client = SimpleNamespace(
        load_markets=lambda: None,
        market=lambda symbol: {"base": "ABC", "quote": "USDT", "limits": {}},
        amount_to_precision=lambda symbol, qty: str(qty),
        create_order=submit,
        fetch_ticker=lambda symbol: {"last": 100},
    )
    return exchange


def fill(**kwargs):
    order = dict(id="123", status="closed", average=100, filled=1, cost=100,
                 fee={"currency": "ABC", "cost": .001})
    order.update(kwargs)
    return order


def test_live_buy_tracks_net_base_and_quote_cost():
    result = live_client(fill()).place_market_buy("ABC/USDT", 100)
    assert result.success and result.amount == .999 and result.cost == 100


@pytest.mark.parametrize("order", [fill(status="open"), fill(average=0, cost=0), fill(fee=None)])
def test_unconfirmed_execution_blocks_retries(order):
    result = live_client(order).place_market_buy("ABC/USDT", 100)
    assert not result.success and result.status == "UNKNOWN"


def test_timeout_preserves_client_id():
    result = live_client(error=ccxt.RequestTimeout("lost response")).place_market_buy(
        "ABC/USDT", 100, client_order_id="saved-intent")
    assert result.status == "UNKNOWN"
    assert result.client_order_id == result.order_id == "saved-intent"


def test_zero_fill_is_not_reported_filled():
    result = live_client(fill(filled=0)).place_market_sell("ABC/USDT", 1)
    assert not result.success and result.amount == 0


def test_live_stale_cache_not_used_on_error():
    exchange = live_client()
    exchange._price_cache["ABC/USDT"] = 100
    exchange.client.fetch_ticker = lambda symbol: (_ for _ in ()).throw(OSError())
    assert exchange.get_ticker_price("ABC/USDT") == 0


def test_only_completed_live_candles_are_returned():
    import time
    exchange = live_client()
    now = int(time.time() * 1000)
    exchange.client.parse_timeframe = lambda tf: 60
    exchange.client.fetch_ohlcv = lambda *a, **k: [[now - 120000, 1, 2, 1, 2, 10], [now - 30000, 2, 3, 2, 3, 20]]
    candles = exchange.get_historical_klines("ABC/USDT")
    assert len(candles) == 1 and candles[0]["timestamp"] == now - 120000
