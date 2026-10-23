"""Market scanner inspecting top 24 Halal Spot pairs and computing live scores."""
import time
from datetime import datetime, timezone
from typing import List, Dict, Any
from src.exchange.base import BaseExchange
from src.core.regime_detector import MarketRegimeDetector
from src.core.scoring_engine import ScoringEngine
from src.core.models import NewsItem
from src.core.ecosystem_registry import EcosystemRegistry

WATCHLIST = EcosystemRegistry.get_all_symbols()


class MarketScanner:
    def __init__(
        self,
        exchange: BaseExchange,
        regime_detector: MarketRegimeDetector,
        scoring_engine: ScoringEngine,
    ):
        self.exchange = exchange
        self.regime_detector = regime_detector
        self.scoring_engine = scoring_engine
        self._last_scan_time = 0.0
        self.cached_results: List[Dict[str, Any]] = []
        self.last_completed_at = None

    def scan_if_needed(self, interval_seconds: float = 15.0) -> List[Dict[str, Any]]:
        now = time.time()
        if now - self._last_scan_time < interval_seconds and self.cached_results:
            return self.cached_results

        self._last_scan_time = now
        results = []
        for sym in WATCHLIST:
            try:
                price = self.exchange.get_ticker_price(sym)
                klines = self.exchange.get_historical_klines(sym, "1m", 40)
                stale = bool(klines and klines[-1].get("close_time") and
                             time.time()*1000-klines[-1]["close_time"] > 180000)
                if price <= 0 or len(klines) < 30 or stale:
                    results.append({"symbol": sym, "price": None, "phase": "UNAVAILABLE",
                                    "score": 0, "approved": False, "status": "بيانات غير متاحة"})
                    continue
                phase, phase_score = self.regime_detector.detect_phase(klines)
                score_res = self.scoring_engine.evaluate(sym, phase, phase_score, klines, 75.0)
                results.append({
                    "symbol": sym, "price": price, "phase": phase.value,
                    "score": score_res.total_score, "approved": score_res.is_approved,
                    "status": "مؤهل للفحص" if score_res.is_approved else score_res.rejection_reason,
                    "pillar": EcosystemRegistry.get_pillar_for_symbol(sym) or "GENERAL",
                    "leader": EcosystemRegistry.get_leader_for_symbol(sym) or sym,
                })
            except Exception:
                continue

        self.cached_results = results
        self.last_completed_at = datetime.now(timezone.utc).isoformat()
        return results

    def find_breakouts(self) -> List[NewsItem]:
        breakouts = []
        for r in self.scan_if_needed(interval_seconds=15.0):
            if r.get("approved"):
                breakouts.append(NewsItem(
                    news_id=f"spot_breakout_{r['symbol']}_{int(time.time()//60)}",
                    title=f"[SPOT FLOW] {r['symbol']} Quantitative Surge | Score {r['score']:.1f}/100",
                    source="binance_spot_flow",
                    symbol=r["symbol"],
                    sentiment_score=85.0,
                    published_at=datetime.now(timezone.utc),
                ))
        return breakouts
