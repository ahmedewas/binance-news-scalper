"""Bayesian Probability Inference Engine: Computes calibrated P(Win | Evidence) score."""
import math
from typing import Dict, Any, Tuple


class BayesianScorer:
    def __init__(self, prior_win_rate: float = 0.50, min_calibrated_prob: float = 0.72):
        self.prior_p = prior_win_rate
        self.min_prob = min_calibrated_prob

    def calculate_probability(
        self,
        phase: str,
        is_squeeze_fired: bool,
        cvd_positive: bool,
        is_sector_leader_surging: bool,
        is_vp_favorable: bool,
        is_obi_healthy: bool,
    ) -> Tuple[float, float, str]:
        """Returns (posterior_probability, calibrated_score_100, verdict_summary)."""
        prior_odds = self.prior_p / (1.0 - self.prior_p)
        lr = 1.0

        # 1. Market Phase Likelihood Ratio
        if phase == "MARKUP":
            lr *= 1.45
        elif phase == "ACCUMULATION":
            lr *= 1.15
        elif phase in {"DISTRIBUTION", "MARKDOWN"}:
            lr *= 0.25

        # 2. TTM Squeeze Fire
        if is_squeeze_fired:
            lr *= 1.65

        # 3. CVD Order Flow
        if cvd_positive:
            lr *= 1.35
        else:
            lr *= 0.85

        # 4. Sector Leader Momentum
        if is_sector_leader_surging:
            lr *= 1.40

        # 5. Volume Profile Value Area Location
        if is_vp_favorable:
            lr *= 1.30

        # 6. Order Book Depth Support
        if is_obi_healthy:
            lr *= 1.25
        else:
            lr *= 0.80

        post_odds = prior_odds * lr
        post_p = post_odds / (1.0 + post_odds)
        score = round(post_p * 100.0, 1)

        approved = post_p >= self.min_prob
        verdict = f"P(Win)={post_p*100:.1f}% ({'APPROVED' if approved else 'BELOW_PROB_THRESHOLD'})"
        return round(post_p, 4), score, verdict
