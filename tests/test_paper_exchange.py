"""Unit tests for Paper Exchange execution logic."""
from src.exchange.paper import PaperExchange


def test_paper_exchange_initial_balance():
    exchange = PaperExchange(initial_usdt=15.0)
    assert exchange.get_balance("USDT") == 15.0


def test_paper_buy_and_sell_cycle():
    exchange = PaperExchange(initial_usdt=15.0)
    # Mock ticker price by overriding method for test stability
    exchange.get_ticker_price = lambda sym: 10.0

    # Buy with $5 USDT
    buy_res = exchange.place_market_buy("SOL/USDT", cost_usdt=5.0)
    assert buy_res.success
    assert buy_res.price == 10.0
    # Fee is 0.1% -> net cost is 4.995 -> amount is 0.4995
    assert exchange.get_balance("USDT") == 10.0
    assert exchange.get_balance("SOL") > 0.49

    # Sell all holdings at higher price $11.0 (+10% gain)
    exchange.get_ticker_price = lambda sym: 11.0
    sol_amount = exchange.get_balance("SOL")
    sell_res = exchange.place_market_sell("SOL/USDT", amount=sol_amount)
    assert sell_res.success
    # Balance should now be > $15.0 (profitable cycle)
    assert exchange.get_balance("USDT") > 15.0
    assert exchange.get_balance("SOL") == 0.0


def test_insufficient_paper_funds():
    exchange = PaperExchange(initial_usdt=5.0)
    res = exchange.place_market_buy("SOL/USDT", cost_usdt=10.0)
    assert not res.success
    assert "Insufficient" in res.message
