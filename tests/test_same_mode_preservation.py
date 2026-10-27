"""Repeated mode selection must not reset a session or bypass safety locks."""
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import pytest
from src.config import config
from src.core.portfolio_allocator import PortfolioAllocator
from src.core.regime_detector import MarketRegimeDetector
from src.core.risk_manager import RiskManager
from src.core.scoring_engine import ScoringEngine
from src.core.state_store import StateStore
from src.engine.bot_worker import BotWorker
from src.exchange.paper import PaperExchange
from src.web.app import create_app
from fastapi.testclient import TestClient


@pytest.fixture
def worker(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    news = SimpleNamespace(market_scanner=None, fetch_latest_news=lambda: [])
    w = BotWorker(PaperExchange(100), PortfolioAllocator(), MarketRegimeDetector(),
                  ScoringEngine(), RiskManager(), news,
                  store=StateStore(tmp_path / 'state-paper.json'),
                  journal=MagicMock(), mode='PAPER')
    yield w
    w.shutdown()


@pytest.mark.parametrize('mode', ['PAPER', 'LIVE'])
@pytest.mark.parametrize('active', [False, True])
def test_same_mode_preserves_session_and_does_not_touch_exchange(worker, mode, active):
    w = worker
    w.mode, w.is_active = mode, active
    w.exchange.usdt_balance = w.cash = 75.
    w.trade_history.append({'symbol': 'SOL/USDT', 'pnl_usd': -25})
    w.tracker.record_trade('SOL/USDT', -25, -25, 'STOP_LOSS')
    w.last_error = 'Preserve diagnostic'
    w.persist()
    saved = w.store.path.read_bytes()
    original_exchange, original_tracker = w.exchange, w.tracker
    fake_config = replace(config, api_key='test-key', api_secret='test-secret')
    with patch('src.engine.worker_admin.config', fake_config), \
         patch('src.exchange.live.LiveExchange', return_value=PaperExchange(75)) as live, \
         patch('src.exchange.paper.PaperExchange', return_value=PaperExchange(500)) as paper:
        result = w.switch_mode(mode.lower())
    assert w.exchange is original_exchange
    assert w.tracker is original_tracker
    assert result == {'mode': mode, 'is_active': active, 'balance': 75.}
    assert w.tracker.initial_balance == 100
    assert len(w.tracker.trades) == len(w.trade_history) == 1
    assert w.last_error == 'Preserve diagnostic'
    assert w.store.path.read_bytes() == saved
    live.assert_not_called()
    paper.assert_not_called()


@pytest.mark.parametrize('guard', ['loss_limit_hit', 'storage_failed', 'pending_orders'])
def test_same_live_mode_cannot_bypass_safety_guard(worker, guard):
    w = worker
    w.mode, w.is_active = 'LIVE', False
    value = {'pending': {'symbol': 'SOL/USDT', 'side': 'BUY'}} if guard == 'pending_orders' else True
    setattr(w, guard, value)
    cfg = replace(config, api_key='test-key', api_secret='test-secret')
    with patch('src.engine.worker_admin.config', cfg), \
         patch('src.exchange.live.LiveExchange', return_value=PaperExchange(100)):
        result = w.switch_mode('LIVE')
    assert not result['is_active']
    assert getattr(w, guard) == value
    with pytest.raises(ValueError):
        w.set_active(True)


def test_api_reselecting_paused_paper_keeps_pause_and_balance(worker):
    worker.is_active = False
    worker.exchange.usdt_balance = worker.cash = 75.
    with TestClient(create_app(worker, dashboard_token='test-token')) as client:
        result = client.post('/api/mode', json={'mode': 'PAPER'}, headers={
            'X-Requested-With': 'ScalperDashboard', 'X-Dashboard-Token': 'test-token'})
    assert result.status_code == 200
    assert result.json() == {'mode': 'PAPER', 'is_active': False, 'balance': 75.}
