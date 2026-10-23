"""Worker safety tests part 2: Circuit breakers, loss locks, and destination checks."""
from datetime import datetime, timezone
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
                                           datetime.now(timezone.utc), 1, cost_basis=20)
    worker.cash = worker.exchange.get_balance()


def test_initial_balance_and_loss_circuit(worker):
    assert worker.snapshot()['performance']['initial_balance'] == 100
    worker.mode = 'LIVE'
    worker.cash = 96
    worker._publish()
    assert worker.loss_limit_hit and not worker.is_active
    with pytest.raises(ValueError):
        worker.set_active(True)


def test_paper_loss_does_not_block_entries(worker):
    worker.cash = 50
    worker.loss_limit_hit = True
    worker._publish()
    assert not worker.loss_limit_hit
    worker.set_active(True)
    assert worker.is_active


@pytest.mark.parametrize('mode, expected', [('PAPER', False), ('LIVE', True)])
def test_restore_loss_lock_only_in_live(worker, mode, expected):
    worker.mode = mode
    worker.loss_limit_hit = True
    worker.is_active = False
    worker.persist()
    worker.loss_limit_hit = False
    worker.restore()
    assert worker.loss_limit_hit is expected
    assert not worker.is_active


@pytest.mark.parametrize('blocker', ['storage_failed', 'pending_orders'])
def test_paper_keeps_other_safety_blocks(worker, blocker):
    setattr(worker, blocker, True if blocker == 'storage_failed' else {'test': {}})
    with pytest.raises(ValueError):
        worker.set_active(True)
    setattr(worker, blocker, False if blocker == 'storage_failed' else {})


def test_confirmed_exit_saved_before_balance_failure(worker):
    position(worker)
    worker.exchange.get_balance = MagicMock(side_effect=RuntimeError('offline'))
    with pytest.raises(RuntimeError, match='offline'):
        worker._exit('SOL/USDT', 'MANUAL_CLOSE')
    saved = worker.store.load()
    assert not saved['positions'] and not saved['pending_orders']
    assert len(saved['trade_history']) == len(saved['tracker_trades']) == 1


def test_risk_high_water_mark_persisted(worker):
    position(worker)
    worker.positions['SOL/USDT'].entry_time = datetime.now(timezone.utc)
    worker.exchange.get_ticker_price = lambda symbol: 100.7
    worker.manage_positions()
    saved = worker.store.load()['positions'][0]
    assert saved['highest_price'] == 100.7
    assert saved['is_breakeven_locked']
