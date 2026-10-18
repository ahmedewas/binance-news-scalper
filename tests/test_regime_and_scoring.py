"""Unit tests for Market Regime Detection and Quantitative Scoring."""
from src.core.models import MarketPhase
from src.core.regime_detector import MarketRegimeDetector
from src.core.scoring_engine import ScoringEngine


def test_markup_phase_detection():
    detector = MarketRegimeDetector()
    klines = [{"close": 10.0 + i * 0.5, "volume": 100} for i in range(40)]
    phase, score = detector.detect_phase(klines)
    assert phase == MarketPhase.MARKUP
    assert score >= 70.0


def test_markdown_phase_detection():
    detector = MarketRegimeDetector()
    klines = [{"close": 30.0 - i * 0.5, "volume": 100} for i in range(40)]
    phase, score = detector.detect_phase(klines)
    assert phase == MarketPhase.MARKDOWN
    assert score >= 70.0


def test_bull_trap_rejection_in_bearish_regime():
    engine = ScoringEngine(min_score=75.0)
    klines = [{"close": 10.0, "volume": 1000} for _ in range(20)]
    result = engine.evaluate(
        symbol="SOL/USDT",
        phase=MarketPhase.MARKDOWN,
        phase_score=80.0,
        klines=klines,
        news_sentiment=100.0,  # Max positive news
    )
    assert not result.is_approved
    assert "Bull Trap Protection" in (result.rejection_reason or "")


def test_high_conviction_entry_approval():
    engine = ScoringEngine(min_score=75.0)
    klines = [{"close": 10.0 + i * 0.1, "volume": 100} for i in range(20)]
    # Create volume surge on latest candle
    klines[-1]["volume"] = 5000.0
    result = engine.evaluate(
        symbol="SOL/USDT",
        phase=MarketPhase.MARKUP,
        phase_score=85.0,
        klines=klines,
        news_sentiment=90.0,
    )
    assert result.is_approved
    assert result.total_score >= 75.0
