"""News opportunity evaluation and execution helper."""
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from src.core.models import Position, NewsItem
from src.exchange.base import BaseExchange
from src.core.regime_detector import MarketRegimeDetector
from src.core.scoring_engine import ScoringEngine

logger = logging.getLogger("OpportunityExecutor")


class OpportunityExecutor:
    @staticmethod
    def evaluate_and_open(
        item: NewsItem,
        slot_id: int,
        slot_size: float,
        exchange: BaseExchange,
        regime_detector: MarketRegimeDetector,
        scoring_engine: ScoringEngine,
        positions: Dict[str, Position],
        latest_news: List[Dict[str, Any]],
    ) -> bool:
        """Evaluates quantitative criteria and executes market buy if approved."""
        klines = exchange.get_historical_klines(item.symbol, "1m", 40)
        phase, phase_score = regime_detector.detect_phase(klines)
        score_res = scoring_engine.evaluate(
            item.symbol, phase, phase_score, klines, item.sentiment_score
        )

        latest_news.append({
            "symbol": item.symbol, "title": item.title, "score": score_res.total_score,
            "approved": score_res.is_approved, "phase": phase.value,
        })
        if len(latest_news) > 20:
            latest_news.pop(0)

        if not score_res.is_approved:
            return False

        order = exchange.place_market_buy(item.symbol, slot_size)
        if order.success:
            entry_vol = float(klines[-1].get("volume", 1.0)) if klines else 1.0
            positions[item.symbol] = Position(
                symbol=item.symbol, entry_price=order.price,
                current_price=order.price, amount=order.amount,
                highest_price=order.price, entry_time=datetime.now(timezone.utc),
                slot_id=slot_id, entry_volume=entry_vol,
            )
            logger.info(f"Opened {item.symbol} at {order.price} (Slot {slot_id})")
            return True

        return False
