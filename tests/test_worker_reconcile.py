from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient
from src.core.models import Position, OrderResult
from src.core.state_store import StateStore
from src.core.portfolio_allocator import PortfolioAllocator
from src.core.regime_detector import MarketRegimeDetector
from src.core.scoring_engine import ScoringEngine
from src.core.risk_manager import RiskManager
from src.engine.bot_worker import BotWorker
from src.exchange.paper import PaperExchange
from src.web.app import create_app


@pytest.fixture
def worker(tmp_path):
    exchange = PaperExchange(100)
    exchange.get_ticker_price = lambda symbol: 100.
    exchange.get_historical_klines = lambda *args: []
    news = MagicMock()
    news.market_scanner = None
    news.fetch_latest_news.return_value = []
    w = BotWorker(exchange, PortfolioAllocator(), MarketRegimeDetector(), ScoringEngine(),
                  RiskManager(), news, store=StateStore(tmp_path / 'state.json'),
                  journal=MagicMock(), mode='PAPER')
    yield w
    w.shutdown()


def position(worker):
    buy = worker.exchange.place_market_buy('SOL/USDT', 20)
    worker.positions['SOL/USDT'] = Position('SOL/USDT', 100, 100, buy.amount, 100,
                                           datetime.now(timezone.utc) - timedelta(minutes=25), 1, cost_basis=20)
    worker.cash = worker.exchange.get_balance()


def test_api_auth_and_csrf_and_cached_status(worker):
    client = TestClient(create_app(worker, dashboard_token='test-secret'))
    worker.exchange.get_balance = MagicMock(side_effect=AssertionError('status must not fetch'))
    assert client.get('/api/status').status_code == 401
    assert client.get('/api/status', headers={'X-Dashboard-Token': 'test-secret'}).status_code == 200
    headers = {'X-Dashboard-Token': 'test-secret', 'X-Requested-With': 'ScalperDashboard'}
    assert client.post('/api/active', json={'active': False}, headers={'X-Dashboard-Token': 'test-secret'}).status_code == 403
    assert client.post('/api/active', json={'active': False}, headers={**headers, 'Origin': 'https://evil.example'}).status_code == 403
    assert client.post('/api/active', json={'active': False}, headers=headers).status_code == 200


def test_unknown_exit_blocks_retry_and_can_be_reconciled(worker):
    position(worker)
    worker.exchange.place_market_sell = MagicMock(return_value=OrderResult(False, 'remote', 'SOL/USDT', 0, 0, 'SELL', 'UNKNOWN'))
    worker.close_position('SOL/USDT')
    worker.close_position('SOL/USDT')
    assert worker.exchange.place_market_sell.call_count == 1
    assert len(worker.pending_orders) == 1
    worker.exchange.reconcile_order = lambda *a: OrderResult(True, 'remote', 'SOL/USDT', 100, .1998, 'SELL', 'FILLED', cost=19.98, fee_quote=.01998)
    result = worker.reconcile_pending()
    assert result['remaining'] == 0
    assert not worker.positions
    assert len(worker.trade_history) == 1


def test_reset_archives_session_and_never_auto_starts(worker):
    worker.loss_limit_hit = True
    worker.is_active = False
    worker.reset_paper_session()
    assert list((worker.store.path.parent / 'sessions').glob('*.json'))
    assert not worker.loss_limit_hit and not worker.is_active
    assert not worker.trade_history


def test_failed_durable_intent_prevents_submit(worker):
    position(worker)
    worker.store.save = MagicMock(side_effect=OSError('disk full'))
    worker.exchange.place_market_sell = MagicMock()
    with pytest.raises(OSError):
        worker.close_position('SOL/USDT')
    worker.exchange.place_market_sell.assert_not_called()
    assert worker.storage_failed and not worker.is_active
    worker.store = None


def test_reject_remote_host_without_token(worker):
    client = TestClient(create_app(worker, dashboard_token=''))
    assert client.get('/api/status', headers={'host': 'evil.example'}).status_code == 403


def test_reset_not_allowed_with_positions(worker):
    position(worker)
    with pytest.raises(ValueError):
        worker.reset_paper_session()


def test_invalid_state_is_not_silently_discarded(tmp_path):
    path = tmp_path / 'state.json'
    path.write_text('broken', encoding='utf-8')
    with pytest.raises(ValueError):
        StateStore(path).load()
