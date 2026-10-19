"""Unit tests for Semantic Catalyst Classifier."""
from src.news.semantic_scorer import SemanticScorer


def test_tier1_listing_score():
    scorer = SemanticScorer()
    score, reason = scorer.classify_catalyst("Binance Will List Arbitrum (ARB) with New Trading Pairs")
    assert score >= 90.0
    assert "TIER_1_CATALYST" in reason


def test_negation_rumor_filter():
    scorer = SemanticScorer()
    score, reason = scorer.classify_catalyst("Solana CEO denies partnership rumors with big bank")
    assert score <= 10.0
    assert "DISCOUNTED" in reason


def test_red_flag_rejection():
    scorer = SemanticScorer()
    score, reason = scorer.classify_catalyst("Major protocol exploit detected, funds drained")
    assert score == 0.0
    assert "CRITICAL_RED_FLAG" in reason


def test_tier2_partnership():
    scorer = SemanticScorer()
    score, reason = scorer.classify_catalyst("NEAR Announces Strategic Investment from Top Tier Fund")
    assert score >= 80.0
    assert "TIER_2_CATALYST" in reason
