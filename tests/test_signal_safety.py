"""Fail-closed regression coverage for signal inputs and exit proposals."""
from datetime import datetime, timezone
from unittest.mock import MagicMock
import pytest
from src.core.models import MarketPhase, Position
from src.core.portfolio_allocator import PortfolioAllocator
from src.core.risk_manager import RiskManager
from src.core.scoring_engine import ScoringEngine
from src.core.volume_decay_exit import VolumeDecayExitDetector
from src.engine.market_scanner import MarketScanner
from src.news.analyzer import NewsAnalyzer


def candles(count=40):
    bars = [{"close": 10 + i * 0.2, "volume": 100.0} for i in range(count)]
    if bars:
        bars[-1]["volume"] = 5000.0
    return bars


@pytest.mark.parametrize("count", [0, 1, 25, 29])
def test_insufficient_candles_never_approve(count):
    result = ScoringEngine().evaluate("SOL/USDT", MarketPhase.MARKUP, 100, candles(count), 100)
    assert not result.is_approved
    assert "candles" in result.rejection_reason


@pytest.mark.parametrize("sentiment", [-10, 0, 5, 10])
def test_negative_news_veto_overrides_strong_flow(sentiment):
    result = ScoringEngine().evaluate(
        "SOL/USDT", MarketPhase.MARKUP, 100, candles(), sentiment,
        cvd_score=100, hurst_score=100, mm_depletion_score=100,
    )
    assert not result.is_approved
    assert "news" in result.rejection_reason.lower()


def test_scanner_rejects_25_bars_and_requests_enough_history():
    exchange = MagicMock()
    exchange.get_ticker_price.return_value = 100
    exchange.get_historical_klines.return_value = candles(25)
    regime, scoring = MagicMock(), MagicMock()
    results = MarketScanner(exchange, regime, scoring).scan_if_needed(0)
    assert results and all(not row["approved"] for row in results)
    assert all(row["phase"] == "UNAVAILABLE" for row in results)
    assert all(call.args[1:] == ("1m", 40) for call in exchange.get_historical_klines.call_args_list)
    regime.detect_phase.assert_not_called()
    scoring.evaluate.assert_not_called()


@pytest.mark.parametrize("text", ["Markets near record highs", "Traders link rally to demand", "An op ed about markets"])
def test_ordinary_lowercase_words_are_not_tickers(text):
    assert NewsAnalyzer().extract_symbol(text) is None


def test_explicit_near_ticker_is_preserved():
    assert NewsAnalyzer().extract_symbol("NEAR announces new upgrade") == "NEAR/USDT"


def test_slot_size_cannot_exceed_free_cash():
    result = PortfolioAllocator(max_slots=5).calculate_slots(7.31, total_equity=100)
    assert result["can_trade"]
    assert result["slot_size"] <= 7.31
    assert result["total_slots"] <= 5


def test_partial_exit_proposal_is_retryable_until_fill():
    pos = Position(symbol="SOL/USDT", entry_price=100, current_price=100,
                   amount=2, highest_price=100, entry_time=datetime.now(timezone.utc), slot_id=1)
    risk = RiskManager(stage1_tp_pct=0.012)
    for _ in range(2):
        should_exit, reason, ratio = risk.evaluate_exit(pos, 101.3)
        assert should_exit and ratio == 0.5 and "PARTIAL_TP_50" in reason
        assert not pos.partial_tp_done
        assert pos.amount == 2


@pytest.mark.parametrize("volumes,elapsed,expected", [
    ([100, 100, 100], 4.99, False),
    ([100], 6, False),
    ([100, 100], 6, False),
    ([100, 500, 100], 6, False),
    ([100, 100, 100], 5, True),
])
def test_volume_decay_needs_five_minutes_and_three_low_bars(volumes, elapsed, expected):
    exit_now, _ = VolumeDecayExitDetector().check_volume_decay(
        1000, [{"volume": v} for v in volumes], elapsed, 0.001,
    )
    assert exit_now is expected
