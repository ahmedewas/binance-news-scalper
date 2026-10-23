"""Unit tests for Bayesian Probability Inference Engine."""
from src.core.bayesian_scorer import BayesianScorer


def test_high_conviction_all_favorable():
    scorer = BayesianScorer()
    prob, score, verdict = scorer.calculate_probability(
        phase="MARKUP",
        is_squeeze_fired=True,
        cvd_positive=True,
        is_sector_leader_surging=True,
        is_vp_favorable=True,
        is_obi_healthy=True,
    )
    # When all evidence aligns, posterior probability should be > 85%
    assert prob >= 0.85
    assert score >= 85.0
    assert "APPROVED" in verdict


def test_markdown_rejection():
    scorer = BayesianScorer()
    prob, score, verdict = scorer.calculate_probability(
        phase="MARKDOWN",
        is_squeeze_fired=False,
        cvd_positive=False,
        is_sector_leader_surging=False,
        is_vp_favorable=False,
        is_obi_healthy=False,
    )
    # Severe penalty for markdown
    assert prob < 0.30
    assert score < 30.0
    assert "BELOW_PROB_THRESHOLD" in verdict


def test_marginal_case():
    scorer = BayesianScorer()
    # Moderate accumulation with only CVD positive
    prob, score, verdict = scorer.calculate_probability(
        phase="ACCUMULATION",
        is_squeeze_fired=False,
        cvd_positive=True,
        is_sector_leader_surging=False,
        is_vp_favorable=False,
        is_obi_healthy=True,
    )
    assert 0.45 <= prob <= 0.70
