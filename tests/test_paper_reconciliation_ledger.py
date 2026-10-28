"""Regression coverage for paper execution evidence and durable reconciliation - Part 1."""
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
from unittest.mock import MagicMock
import pytest
from src.core.models import Position
from src.exchange.paper import PaperExchange
from src.engine.bot_worker import BotWorker
from src.core.state_store import StateStore
from src.core.portfolio_allocator import PortfolioAllocator
from src.core.regime_detector import MarketRegimeDetector
from src.core.scoring_engine import ScoringEngine
from src.core.risk_manager import RiskManager


@pytest.fixture
def make_worker(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    workers = []

    def make():
        exchange = PaperExchange(100)
        exchange.get_ticker_price = lambda symbol: 100.0
        news = MagicMock()
        news.market_scanner = None
        w = BotWorker(exchange, PortfolioAllocator(), MarketRegimeDetector(), ScoringEngine(),
                      RiskManager(), news, StateStore(tmp_path / 'state.json'), MagicMock(), 'PAPER')
        workers.append(w)
        return w

    yield make
    for w in workers:
        w.pool.shutdown(wait=False)


def add_position(w):
    result = w.exchange.place_market_buy('SOL/USDT', 20, client_order_id='initial-buy')
    w.positions['SOL/USDT'] = Position('SOL/USDT', 100, 100, result.amount, 100,
                                       datetime.now(timezone.utc), 1, cost_basis=20)
    return result


@pytest.mark.parametrize('side', ['BUY', 'SELL'])
def test_unsubmitted_intent_never_fabricates_execution(make_worker, side):
    w = make_worker()
    if side == 'SELL':
        add_position(w)
    before = deepcopy((w.positions, w.exchange.holdings, w.exchange.usdt_balance))
    cid = w._before_order('SOL/USDT', side, 20 if side == 'BUY' else .1998)
    result = w.reconcile_pending()
    assert result['remaining'] == 1 and cid in w.pending_orders
    assert (w.positions, w.exchange.holdings, w.exchange.usdt_balance) == before
    assert w.trade_history == [] and not w.is_active


@pytest.mark.parametrize('side', ['BUY', 'SELL'])
def test_recorded_execution_survives_restart_and_applies_once(make_worker, side):
    w = make_worker()
    if side == 'SELL':
        add_position(w)
    qty = 20 if side == 'BUY' else w.positions['SOL/USDT'].amount
    cid = w._before_order('SOL/USDT', side, qty)
    submit = w.exchange.place_market_buy if side == 'BUY' else w.exchange.place_market_sell
    execution = submit('SOL/USDT', qty, client_order_id=cid)
    w.persist()
    restored = make_worker()
    restored.exchange.get_ticker_price = MagicMock(side_effect=AssertionError('No market lookup'))
    assert asdict(restored.exchange.reconcile_order('SOL/USDT', cid)) == asdict(execution)
    balances = deepcopy((restored.exchange.holdings, restored.exchange.usdt_balance))
    assert restored.reconcile_pending()['remaining'] == 0
    assert restored.reconcile_pending()['remaining'] == 0
    assert (restored.exchange.holdings, restored.exchange.usdt_balance) == balances
    if side == 'BUY':
        assert restored.positions['SOL/USDT'].cost_basis == 20
        assert restored.positions['SOL/USDT'].amount == execution.amount
    else:
        assert not restored.positions and len(restored.trade_history) == 1


def test_repeated_client_id_is_idempotent_and_conflicts_stay_unknown():
    ex = PaperExchange(100)
    ex.get_ticker_price = lambda symbol: 100
    buy = ex.place_market_buy('SOL/USDT', 20, 'buy-id')
    assert ex.place_market_buy('SOL/USDT', 20, 'buy-id') == buy
    assert ex.usdt_balance == 80
    assert ex.place_market_buy('SOL/USDT', 21, 'buy-id').status == 'UNKNOWN'
    assert ex.place_market_sell('SOL/USDT', 20, 'buy-id').status == 'UNKNOWN'
    assert ex.reconcile_order('OTHER/USDT', 'buy-id').status == 'UNKNOWN'
    sell = ex.place_market_sell('SOL/USDT', buy.amount, 'sell-id')
    balance = ex.usdt_balance
    assert ex.place_market_sell('SOL/USDT', buy.amount, 'sell-id') == sell
    assert ex.usdt_balance == balance and ex.reconcile_order('SOL/USDT', 'buy-id') == buy
