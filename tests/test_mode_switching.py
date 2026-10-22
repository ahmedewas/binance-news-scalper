"""Unit tests for runtime mode switching between PAPER and LIVE."""
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from src.core.models import Position
from src.core.portfolio_allocator import PortfolioAllocator
from src.core.regime_detector import MarketRegimeDetector
from src.core.scoring_engine import ScoringEngine
from src.core.risk_manager import RiskManager
from src.engine.bot_worker import BotWorker
from src.exchange.paper import PaperExchange
from src.web.app import create_app


@pytest.fixture
def worker():
    exchange = PaperExchange(15.0)
    news = MagicMock()
    news.fetch_latest_news.return_value = []
    w = BotWorker(exchange, PortfolioAllocator(), MarketRegimeDetector(),
                  ScoringEngine(), RiskManager(), news, mode='PAPER')
    yield w
    w.shutdown()


def test_switch_mode_rejects_open_positions(worker):
    worker.positions['SOL/USDT'] = MagicMock(spec=Position)
    with pytest.raises(ValueError, match="يجب إغلاق كافة الصفقات"):
        worker.switch_mode('LIVE')


def test_switch_mode_live_requires_api_credentials(worker):
    from types import SimpleNamespace
    fake_cfg = SimpleNamespace(api_key="", api_secret="")
    with patch("src.engine.worker_admin.config", fake_cfg):
        with pytest.raises(ValueError, match="مفاتيح بينانس API غير مدخلة"):
            worker.switch_mode('LIVE')


def test_switch_mode_paper_cycle(worker):
    res = worker.switch_mode('PAPER')
    assert res['mode'] == 'PAPER'
    assert res['is_active'] is True
    assert worker.mode == 'PAPER'
    assert isinstance(worker.exchange, PaperExchange)


def test_api_mode_endpoint(worker):
    client = TestClient(create_app(worker))
    res = client.post('/api/mode', json={'mode': 'PAPER'},
                      headers={'X-Requested-With': 'ScalperDashboard'})
    assert res.status_code == 200
    assert res.json()['mode'] == 'PAPER'

    # Invalid mode rejected
    bad_res = client.post('/api/mode', json={'mode': 'INVALID'},
                          headers={'X-Requested-With': 'ScalperDashboard'})
    assert bad_res.status_code == 422
