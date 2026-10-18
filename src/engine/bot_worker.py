"""Trading bot worker loop managing lifecycle, positions, and news execution."""
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any
from src.core.models import Position
from src.exchange.base import BaseExchange
from src.core.portfolio_allocator import PortfolioAllocator
from src.core.regime_detector import MarketRegimeDetector
from src.core.scoring_engine import ScoringEngine
from src.core.risk_manager import RiskManager
from src.news.fetcher import NewsFetcher

logger = logging.getLogger("BotWorker")


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
        self.is_active = True
        self.positions: Dict[str, Position] = {}
        self.trade_history: List[Dict[str, Any]] = []
        self.latest_news: List[Dict[str, Any]] = []

    def manage_positions(self) -> None:
        """Inspects all open positions against Dynamic Triple-Exit rules."""
        for sym, pos in list(self.positions.items()):
            cur_price = self.exchange.get_ticker_price(sym)
            should_exit, reason = self.risk_manager.evaluate_exit(pos, cur_price)
            if should_exit:
                res = self.exchange.place_market_sell(sym, pos.amount)
                pnl = (cur_price - pos.entry_price) / pos.entry_price
                self.trade_history.append({
                    "symbol": sym, "pnl_pct": round(pnl * 100, 2),
                    "reason": reason, "exit_price": cur_price,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                del self.positions[sym]
                logger.info(f"Closed {sym}: {reason} | PnL: {pnl*100:.2f}%")

    def process_news_opportunities(self) -> None:
        """Scans news and executes trades if quantitative criteria are met."""
        usdt = self.exchange.get_balance("USDT")
        alloc = self.allocator.calculate_slots(usdt)
        if not alloc["can_trade"]:
            return

        active_slots = {p.slot_id for p in self.positions.values()}
        slot_id = self.allocator.get_available_slot(alloc["total_slots"], active_slots)
        if slot_id == -1:
            return

        for item in self.news_fetcher.fetch_latest_news():
            if item.symbol in self.positions:
                continue
            klines = self.exchange.get_historical_klines(item.symbol, "1m", 40)
            phase, phase_score = self.regime_detector.detect_phase(klines)
            score_res = self.scoring_engine.evaluate(
                item.symbol, phase, phase_score, klines, item.sentiment_score
            )
            self.latest_news.append({
                "symbol": item.symbol, "title": item.title, "score": score_res.total_score,
                "approved": score_res.is_approved, "phase": phase.value
            })
            if len(self.latest_news) > 20:
                self.latest_news.pop(0)

            if score_res.is_approved:
                order = self.exchange.place_market_buy(item.symbol, alloc["slot_size"])
                if order.success:
                    self.positions[item.symbol] = Position(
                        symbol=item.symbol, entry_price=order.price,
                        current_price=order.price, amount=order.amount,
                        highest_price=order.price, entry_time=datetime.now(timezone.utc),
                        slot_id=slot_id,
                    )
                    logger.info(f"Opened {item.symbol} at {order.price} (Slot {slot_id})")
                    break

    def step(self) -> None:
        if not self.is_active:
            return
        self.manage_positions()
        self.process_news_opportunities()
