"""Unit tests for Lead-Lag cross-asset latency correlator."""
from src.core.lead_lag_correlator import LeadLagCorrelator


def test_lead_lag_arbitrage_trigger():
    correlator = LeadLagCorrelator(leader_threshold=0.012, laggard_ceiling=0.004)
    # SOL rallies +2.0%, while JUP has only moved +0.2%
    is_opp, conf, reason = correlator.evaluate_opportunity(
        leader_symbol="SOL/USDT",
        leader_return=0.020,
        laggard_symbol="JUP/USDT",
        laggard_return=0.002,
    )
    assert is_opp
    assert conf >= 70.0
    assert "Lead-Lag Edge" in reason


def test_lead_lag_no_arbitrage_when_already_moved():
    correlator = LeadLagCorrelator(leader_threshold=0.012, laggard_ceiling=0.004)
    # SOL rallies +2.0%, but JUP has already rallied +1.5% (no edge left)
    is_opp, conf, reason = correlator.evaluate_opportunity(
        leader_symbol="SOL/USDT",
        leader_return=0.020,
        laggard_symbol="JUP/USDT",
        laggard_return=0.015,
    )
    assert not is_opp
    assert conf == 0.0


def test_invalid_follower_pair():
    correlator = LeadLagCorrelator()
    is_opp, conf, reason = correlator.evaluate_opportunity(
        leader_symbol="SOL/USDT",
        leader_return=0.05,
        laggard_symbol="DOGE/USDT",
        laggard_return=0.0,
    )
    assert not is_opp
    assert "Not a correlated follower" in reason
