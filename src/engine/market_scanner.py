"""Market scanner inspecting top liquid pairs and computing live regime scores."""
import time
from typing import List, Dict, Any
from src.exchange.base import BaseExchange
from src.core.regime_detector import MarketRegimeDetector
from src.core.scoring_engine import ScoringEngine

WATCHLIST = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "NEAR/USDT", "FET/USDT"]


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
                score_res = self.scoring_engine.evaluate(sym, phase, phase_score, klines, 0.70)
                results.append({
                    "symbol": sym,
                    "price": price,
                    "phase": phase.value,
                    "score": score_res.total_score,
                    "approved": score_res.is_approved,
                    "status": "APPROVED 🚀" if score_res.is_approved else f"Score {score_res.total_score}/100 (<75)",
                })
            except Exception:
                continue

        self.cached_results = results
        return results
