"""Trading bot worker loop managing lifecycle, positions, and news execution."""
from datetime import datetime, timezone
from typing import Dict, List, Any
from src.core.models import Position
from src.exchange.base import BaseExchange
from src.core.portfolio_allocator import PortfolioAllocator
from src.core.regime_detector import MarketRegimeDetector
from src.core.scoring_engine import ScoringEngine
from src.core.risk_manager import RiskManager
from src.core.volume_decay_exit import VolumeDecayExitDetector
from src.news.fetcher import NewsFetcher
from src.core.performance_tracker import PerformanceTracker
from src.core.audit_journal import AuditJournal
from src.engine.position_handler import PositionHandler
from src.engine.opportunity_executor import OpportunityExecutor


class BotWorker:
    def __init__(
        self,
        exchange: BaseExchange,
        allocator: PortfolioAllocator,
        regime_detector: MarketRegimeDetector,
        scoring_engine: ScoringEngine,
        risk_manager: RiskManager,
        news_fetcher: NewsFetcher,
    ):
        self.exchange = exchange
        self.allocator = allocator
        self.regime_detector = regime_detector
        self.scoring_engine = scoring_engine
        self.risk_manager = risk_manager
        self.news_fetcher = news_fetcher
        self.volume_decay_detector = VolumeDecayExitDetector()
        self.tracker = PerformanceTracker()
        self.journal = AuditJournal()
        self.is_active = True
        self.positions: Dict[str, Position] = {}
        self.trade_history: List[Dict[str, Any]] = []
        self.latest_news: List[Dict[str, Any]] = []

    def manage_positions(self) -> None:
        """Inspects open positions against Dynamic Multi-Stage Triple-Exit rules."""
        now = datetime.now(timezone.utc)
        for sym, pos in list(self.positions.items()):
            cur_price = self.exchange.get_ticker_price(sym)
            should_exit, reason, ratio = self.risk_manager.evaluate_exit(pos, cur_price, now)

            if not should_exit and pos.entry_volume > 0:
                elapsed = (now - pos.entry_time).total_seconds() / 60.0
                pnl = (cur_price - pos.entry_price) / pos.entry_price
                klines = self.exchange.get_historical_klines(sym, "1m", 5)
                decay_exit, decay_reason = self.volume_decay_detector.check_volume_decay(
                    pos.entry_volume, klines, elapsed, pnl
                )
                if decay_exit:
                    should_exit, reason, ratio = True, decay_reason, 1.0

            if should_exit:
                PositionHandler.execute_exit(
                    self.exchange, self.positions, sym, reason, ratio, self.trade_history
                )
                if self.trade_history:
                    last = self.trade_history[-1]
                    self.tracker.record_trade(last["symbol"], last["pnl_pct"], last["pnl_usd"], last["reason"])
                    self.journal.log_trade_closed(last, self.exchange.get_balance("USDT"))

    def process_news_opportunities(self) -> None:
        """Scans news and executes trades if quantitative criteria are met."""
        usdt = self.exchange.get_balance("USDT")
        alloc = self.allocator.calculate_slots(usdt)
        if not alloc["can_trade"]:
            return

        active_slots = {p.slot_id for p in self.positions.values()}
        locked_slots = {p.slot_id for p in self.positions.values() if p.is_breakeven_locked}
        slot_id = self.allocator.get_available_slot(alloc["total_slots"], active_slots, locked_slots)
        if slot_id == -1:
            return

        for item in self.news_fetcher.fetch_latest_news():
            if item.symbol in self.positions:
                continue
            opened = OpportunityExecutor.evaluate_and_open(
                item, slot_id, alloc["slot_size"], self.exchange,
                self.regime_detector, self.scoring_engine,
                self.positions, self.latest_news, self.journal
            )
            if opened:
                break

    def step(self) -> None:
        if not self.is_active:
            return
        self.manage_positions()
        self.process_news_opportunities()
