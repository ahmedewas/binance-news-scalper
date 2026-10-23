"""Edge case tests for worker state store corruption, destination checks, and reset guards."""
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
import pytest
from src.core.models import Position
from src.core.state_store import StateStore
from src.core.portfolio_allocator import PortfolioAllocator
from src.core.regime_detector import MarketRegimeDetector
from src.core.scoring_engine import ScoringEngine
from src.core.risk_manager import RiskManager
from src.engine.bot_worker import BotWorker
from src.exchange.paper import PaperExchange


@pytest.fixture
def worker(tmp_path):
    exchange = PaperExchange(100)
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


def test_reset_not_allowed_with_positions(worker):
    position(worker)
    with pytest.raises(ValueError):
        worker.reset_paper_session()


def test_invalid_state_is_not_silently_discarded(tmp_path):
    path = tmp_path / 'state.json'
    path.write_text('broken', encoding='utf-8')
    with pytest.raises(ValueError):
        StateStore(path).load()


def test_switch_preserves_existing_destination(worker):
    destination = StateStore(worker.store.path.parent / 'state-paper.json')
    destination.save({'version': 1, 'positions': [{'symbol': 'SOL/USDT'}]})
    original = destination.path.read_bytes()
    exchange = worker.exchange
    with pytest.raises(ValueError, match='حالة محفوظة'):
        worker.switch_mode('PAPER')
    assert destination.path.read_bytes() == original
    assert worker.exchange is exchange


def test_snapshot_uses_effective_atr_and_ratchet_levels(worker):
    position(worker)
    pos = worker.positions['SOL/USDT']
    pos.target_tp, pos.stop_loss = 102.5, 98.5
    pos.highest_price, pos.is_breakeven_locked = 103, True
    worker._publish()
    row = worker.snapshot()['open_positions'][0]
    target, stop, _ = worker.risk_manager.exit_levels(pos)
    assert row['target_tp'] == target
    assert target == pytest.approx(102.5)
    assert row['stop_loss'] == stop
