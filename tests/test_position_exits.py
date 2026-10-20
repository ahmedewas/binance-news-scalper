"""Position exit and order handling execution safety tests."""
from datetime import datetime, timezone
from types import SimpleNamespace
import pytest
from src.core.models import Position, OrderResult
from src.exchange.paper import PaperExchange
from src.engine.position_handler import PositionHandler


def position():
    return Position("ABC/USDT", 100, 100, 1, 100, datetime.now(timezone.utc), 1, cost_basis=101)


def test_partial_fill_keeps_remainder_and_actual_net_pnl():
    pos = position()
    exchange = SimpleNamespace(
        get_ticker_price=lambda s: 110,
        place_market_sell=lambda s, q: OrderResult(True, "1", s, 90, .4, "SELL", "FILLED", cost=36, fee_quote=.1)
    )
    positions, history = {pos.symbol: pos}, []
    result = PositionHandler.execute_exit(exchange, positions, pos.symbol, "STOP_LOSS", 1, history)
    assert result["success"] and pos.amount == pytest.approx(.6)
    assert pos.cost_basis == pytest.approx(60.6)
    assert history[0]["exit_price"] == 90
    assert history[0]["pnl_usd"] == pytest.approx(-4.5)


def test_failed_partial_does_not_mark_done():
    pos = position()
    exchange = SimpleNamespace(
        get_ticker_price=lambda s: 110,
        place_market_sell=lambda s, q: OrderResult(False, "", s, 0, 0, "SELL", "REJECTED")
    )
    result = PositionHandler.execute_exit(exchange, {pos.symbol: pos}, pos.symbol, "PARTIAL_TP_50", .5, [])
    assert not result["success"] and not pos.partial_tp_done and pos.amount == 1


def test_unknown_sell_freezes_position():
    pos = position()
    calls = []
    def sell(s, q):
        calls.append(q)
        return OrderResult(False, "pending", s, 0, 0, "SELL", "UNKNOWN")
    exchange = SimpleNamespace(get_ticker_price=lambda s: 110, place_market_sell=sell)
    positions = {pos.symbol: pos}
    for _ in range(2):
        result = PositionHandler.execute_exit(exchange, positions, pos.symbol, "STOP_LOSS", 1, [])
        assert result["status"] == "UNKNOWN"
    assert pos.execution_uncertain and len(calls) == 1


def test_small_partial_falls_back_to_full_exit():
    exchange = PaperExchange(5)
    exchange.get_ticker_price = lambda s: 100
    buy = exchange.place_market_buy("ABC/USDT", 5)
    pos = position()
    pos.amount, pos.cost_basis = buy.amount, 5
    exchange.get_ticker_price = lambda s: 102
    positions, history = {pos.symbol: pos}, []
    result = PositionHandler.execute_exit(exchange, positions, pos.symbol, "PARTIAL_TP_50", .5, history)
    assert result["success"] and not positions
    assert history[0]["ratio"] == 1
    assert history[0]["pnl_usd"] == pytest.approx(5 * .999 * 1.02 * .999 - 5)


@pytest.mark.parametrize("quantity", [0, -1, float("nan"), float("inf")])
def test_paper_invalid_quantities_do_not_mutate(quantity):
    exchange = PaperExchange(10)
    exchange.get_ticker_price = lambda s: 100
    assert not exchange.place_market_buy("ABC/USDT", quantity).success
    assert not exchange.place_market_sell("ABC/USDT", quantity).success
    assert exchange.usdt_balance == 10 and exchange.holdings == {}


def test_paper_missing_sell_price_preserves_holdings():
    exchange = PaperExchange(10)
    exchange.holdings["ABC"] = 1
    exchange.get_ticker_price = lambda s: 0
    assert not exchange.place_market_sell("ABC/USDT", 1).success
    assert exchange.holdings["ABC"] == 1 and exchange.usdt_balance == 10
