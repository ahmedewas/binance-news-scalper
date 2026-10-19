"""Market scanner inspecting top 24 Halal Spot pairs and computing live scores."""
import time
from datetime import datetime, timezone
from typing import List, Dict, Any
from src.exchange.base import BaseExchange
from src.core.regime_detector import MarketRegimeDetector
from src.core.scoring_engine import ScoringEngine
from src.core.models import NewsItem

WATCHLIST = [
    "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "ADA/USDT",
    "AVAX/USDT", "SUI/USDT", "LINK/USDT", "NEAR/USDT", "FET/USDT", "APT/USDT",
    "DOT/USDT", "RENDER/USDT", "TAO/USDT", "TIA/USDT", "SEI/USDT", "INJ/USDT",
    "ATOM/USDT", "OP/USDT", "ARB/USDT", "ALGO/USDT", "POL/USDT", "FTM/USDT",
]


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

    def scan_if_needed(self, interval_seconds: float = 15.0) -> List[Dict[str, Any]]:
        now = time.time()
        if now - self._last_scan_time < interval_seconds and self.cached_results:
            return self.cached_results

        self._last_scan_time = now
        results = []
        for sym in WATCHLIST:
            try:
                price = self.exchange.get_ticker_price(sym)
                klines = self.exchange.get_historical_klines(sym, "1m", 25)
                phase, phase_score = self.regime_detector.detect_phase(klines)
                score_res = self.scoring_engine.evaluate(sym, phase, phase_score, klines, 75.0)
                results.append({
                    "symbol": sym, "price": price, "phase": phase.value,
                    "score": score_res.total_score, "approved": score_res.is_approved,
                    "status": "APPROVED 🚀" if score_res.is_approved else f"Score {score_res.total_score}/100 (<75)",
                })
            except Exception:
                continue

        self.cached_results = results
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
