"""Worker safety tests part 1: Exits, pauses, and error states."""
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
import pytest
from src.core.models import Position, OrderResult
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
                                           datetime.now(timezone.utc) - timedelta(minutes=25), 1, cost_basis=20)
    worker.cash = worker.exchange.get_balance()


def test_pause_still_exits_timeout_and_records_net_fees(worker):
    position(worker)
    worker.is_active = False
    worker.step()
    assert not worker.positions
    assert len(worker.tracker.trades) == 1
    assert worker.tracker.trades[0]['pnl_usd'] == pytest.approx(-.03998)
    assert worker.exchange.usdt_balance == pytest.approx(99.96002)


def test_failed_exit_never_duplicates_previous_trade(worker):
    position(worker)
    worker.trade_history.append(dict(symbol='OLD', pnl_pct=1, pnl_usd=1, reason='OLD'))
    worker.exchange.place_market_sell = lambda *a, **k: OrderResult(False, '', 'SOL/USDT', 0, 0, 'SELL', 'REJECTED')
    worker.manage_positions()
    assert len(worker.trade_history) == 1
    assert worker.tracker.trades == []
    assert not worker.pending_orders


def test_close_all_reports_failure_and_stays_paused(worker):
    position(worker)
    worker.exchange.get_ticker_price = lambda symbol: 0
    result = worker.close_all()
    assert result['status'] == 'PARTIAL_FAILURE'
    assert result['remaining'] == ['SOL/USDT']
    assert not worker.is_active


def test_state_restores_paper_holdings_and_pending_intent(worker):
    position(worker)
    cid = worker._before_order('SOL/USDT', 'SELL', .1)
    restored = BotWorker(PaperExchange(15), PortfolioAllocator(), MarketRegimeDetector(),
                         ScoringEngine(), RiskManager(), worker.news_fetcher, store=worker.store,
                         journal=MagicMock(), mode='PAPER')
    try:
        assert restored.exchange.usdt_balance == 80
        assert restored.positions['SOL/USDT'].amount == pytest.approx(.1998)
        assert cid in restored.pending_orders
        assert restored.positions['SOL/USDT'].execution_uncertain
        assert not restored.is_active
    finally:
        restored.pool.shutdown(wait=False)
