"""Regression coverage for paper execution evidence and durable reconciliation - Part 2."""
from dataclasses import asdict
from unittest.mock import MagicMock
import pytest
from src.core.models import OrderResult
from src.engine.bot_worker import BotWorker
from src.exchange.paper import PaperExchange
from src.core.state_store import StateStore
from src.core.portfolio_allocator import PortfolioAllocator
from src.core.regime_detector import MarketRegimeDetector
from src.core.scoring_engine import ScoringEngine
from src.core.risk_manager import RiskManager
from tests.test_paper_reconciliation_ledger import add_position


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


@pytest.mark.parametrize('changes', [
    {'status': 'REJECTED', 'price': 0, 'amount': 0}, {'price': 0}, {'amount': 0},
    {'price': float('nan')}, {'side': 'SELL'}, {'symbol': 'OTHER/USDT'}, {'cost': 0},
    {'client_order_id': 'wrong-id'}, {'fee_quote': float('inf')}
])
def test_invalid_reconcile_result_cannot_create_position(make_worker, changes):
    w = make_worker()
    cid = w._before_order('SOL/USDT', 'BUY', 20)
    row = asdict(OrderResult(True, 'order', 'SOL/USDT', 100, .1998, 'BUY', 'FILLED', cost=20))
    row.update(changes)
    w.exchange.reconcile_order = lambda *args: OrderResult(**row)
    assert w.reconcile_pending()['remaining'] == 1 and cid in w.pending_orders
    assert not w.positions and w.store.load()['positions'] == []


def test_legacy_state_without_ledger_remains_readable_and_unknown(make_worker):
    w = make_worker()
    add_position(w)
    cid = w._before_order('SOL/USDT', 'SELL', .1998)
    state = w.store.load()
    del state['paper']['orders']
    w.store.save(state)
    restored = make_worker()
    assert restored.reconcile_pending()['remaining'] == 1 and cid in restored.pending_orders
    assert restored.positions['SOL/USDT'].amount == .1998 and not restored.trade_history


def test_crash_before_snapshot_does_not_restore_unsaved_fill(make_worker):
    w = make_worker()
    cid = w._before_order('SOL/USDT', 'BUY', 20)
    w.exchange.place_market_buy('SOL/USDT', 20, cid)
    restored = make_worker()
    assert restored.exchange.usdt_balance == 100
    assert not restored.exchange.holdings and not restored.exchange.orders
    assert restored.reconcile_pending()['remaining'] == 1 and not restored.positions


def test_confirmed_rejection_clears_intent_without_position(make_worker):
    w = make_worker()
    cid = w._before_order('SOL/USDT', 'BUY', 20)
    w.exchange.reconcile_order = lambda *args: OrderResult(
        False, cid, 'SOL/USDT', 0, 0, 'BUY', 'REJECTED', client_order_id=cid)
    assert w.reconcile_pending()['remaining'] == 0
    assert not w.positions and not w.trade_history


def test_reset_archives_ledger_before_clearing(make_worker):
    w = make_worker()
    w.exchange.place_market_buy('SOL/USDT', 20, 'buy')
    w.exchange.place_market_sell('SOL/USDT', w.exchange.holdings['SOL'], 'sell')
    w.reset_paper_session()
    archive = next((w.store.path.parent / 'sessions').glob('*.json'))
    assert set(StateStore(archive).load()['paper']['orders']) == {'buy', 'sell'}
    assert w.exchange.orders == {} and w.store.load()['paper']['orders'] == {}
