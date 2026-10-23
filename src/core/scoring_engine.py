"""Multi-factor quantitative scoring formula for entry validation."""
from typing import List, Dict, Any, Optional
from src.core.models import MarketPhase, ScoringResult


class ScoringEngine:
    def __init__(self, min_score: float = 70.0):
        self.min_score = min_score

    def evaluate(
        self,
        symbol: str,
        phase: MarketPhase,
        phase_score: float,
        klines: List[Dict[str, Any]],
        news_sentiment: float,
        cvd_score: Optional[float] = None,
        hurst_score: Optional[float] = None,
        mm_depletion_score: Optional[float] = None,
    ) -> ScoringResult:
        """Computes weighted probability score and approves or rejects trade."""
        if 0.0 < news_sentiment <= 1.0:
            news_sentiment = news_sentiment * 100.0

        if len(klines) < 30 or any(float(k.get("close", 0)) <= 0 for k in klines):
            return ScoringResult(symbol, phase, phase_score, 0, 0, news_sentiment,
                                 0, False, "Insufficient or invalid closed candles")
        if news_sentiment <= 10:
            return ScoringResult(symbol, phase, phase_score, 0, 0, news_sentiment,
                                 0, False, "Negative or unconfirmed news: entry blocked")

        if phase in (MarketPhase.DISTRIBUTION, MarketPhase.MARKDOWN):
            return ScoringResult(
                symbol=symbol, phase=phase, phase_score=phase_score,
                momentum_score=0.0, volume_score=0.0, news_score=news_sentiment,
                total_score=0.0, is_approved=False,
                rejection_reason=f"Bull Trap Protection: Phase {phase.value}",
            )

        if hurst_score is not None and hurst_score < 30.0:
            return ScoringResult(
                symbol=symbol, phase=phase, phase_score=phase_score,
                momentum_score=0.0, volume_score=0.0, news_score=news_sentiment,
                total_score=0.0, is_approved=False,
                rejection_reason="Chaos Filter: Market in anti-persistent Brownian noise",
            )

        if cvd_score is not None and cvd_score < 40.0:
            return ScoringResult(
                symbol=symbol, phase=phase, phase_score=phase_score,
                momentum_score=0.0, volume_score=0.0, news_score=news_sentiment,
                total_score=0.0, is_approved=False,
                rejection_reason=f"CVD Rejection: Aggressive Seller Dominance ({cvd_score})",
            )

        vols = [float(k.get("volume", 0)) for k in klines[-10:]]
        avg_vol = sum(vols[:-1]) / max(1, len(vols) - 1) if len(vols) > 1 else 1.0
        cur_vol = vols[-1] if vols else 1.0
        volume_score = min(100.0, (cur_vol / max(1e-6, avg_vol)) * 40.0)

        closes = [float(k.get("close", 0)) for k in klines[-5:]]
        ret = (closes[-1] - closes[0]) / closes[0] if closes[0] > 0 else 0.0
        momentum_score = min(100.0, max(0.0, 50.0 + ret * 1000.0))

        # 40% Volume & Order Flow + 30% Market Regime + 30% Momentum & Catalyst
        vol_comp = (volume_score * 0.5 + cvd_score * 0.5) if cvd_score is not None else volume_score
        mom_cat = momentum_score * 0.5 + news_sentiment * 0.5
        weighted = vol_comp * 0.40 + phase_score * 0.30 + mom_cat * 0.30

        if hurst_score is not None and mm_depletion_score is not None:
            weighted = weighted * 0.85 + (hurst_score * 0.075 + mm_depletion_score * 0.075)

        from src.core.volatility_squeeze import VolatilitySqueezeDetector
        from src.core.bayesian_scorer import BayesianScorer
        _, is_fired, _, _ = VolatilitySqueezeDetector().evaluate(klines)
        if is_fired:
            weighted = min(100.0, weighted + 10.0)
        cvd_pos = bool(cvd_score is None or cvd_score >= 50.0)
        _, bayes_score, _ = BayesianScorer().calculate_probability(
            phase=phase.value, is_squeeze_fired=is_fired, cvd_positive=cvd_pos,
            is_sector_leader_surging=False, is_vp_favorable=True, is_obi_healthy=True
        )
        total = round(min(100.0, max(0.0, weighted * 0.75 + bayes_score * 0.25)), 2)
        approved = total >= self.min_score
        reason = None if approved else f"Score {total} < Threshold {self.min_score}"

        return ScoringResult(
            symbol=symbol, phase=phase, phase_score=phase_score,
            momentum_score=momentum_score, volume_score=volume_score,
            news_score=news_sentiment, total_score=total,
            is_approved=approved, rejection_reason=reason,
        )

