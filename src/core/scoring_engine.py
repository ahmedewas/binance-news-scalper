"""Multi-factor quantitative scoring formula for entry validation."""
from typing import List, Dict, Any, Optional
from src.core.models import MarketPhase, ScoringResult


class ScoringEngine:
    def __init__(self, min_score: float = 75.0):
        self.min_score = min_score

    def evaluate(
        self,
        symbol: str,
        phase: MarketPhase,
        phase_score: float,
        klines: List[Dict[str, Any]],
        news_sentiment: float,
        cvd_score: Optional[float] = None,
    ) -> ScoringResult:
        """Computes weighted probability score and approves or rejects trade."""
        if phase in (MarketPhase.DISTRIBUTION, MarketPhase.MARKDOWN):
            return ScoringResult(
                symbol=symbol, phase=phase, phase_score=phase_score,
                momentum_score=0.0, volume_score=0.0, news_score=news_sentiment,
                total_score=0.0, is_approved=False,
                rejection_reason=f"Bull Trap Protection: Phase {phase.value}",
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

        if cvd_score is not None:
            total = (
                0.20 * phase_score + 0.20 * momentum_score +
                0.20 * volume_score + 0.20 * news_sentiment + 0.20 * cvd_score
            )
        else:
            total = (
                0.25 * phase_score + 0.25 * momentum_score +
                0.25 * volume_score + 0.25 * news_sentiment
            )

        total = round(total, 2)
        approved = total >= self.min_score
        reason = None if approved else f"Score {total} < Threshold {self.min_score}"

        return ScoringResult(
            symbol=symbol, phase=phase, phase_score=phase_score,
            momentum_score=momentum_score, volume_score=volume_score,
            news_score=news_sentiment, total_score=total,
            is_approved=approved, rejection_reason=reason,
        )

