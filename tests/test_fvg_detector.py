"""Unit tests for Institutional Fair Value Gap (FVG) Detector."""
from src.core.fvg_detector import FVGDetector


def test_bullish_fvg_detection():
    detector = FVGDetector(min_gap_pct=0.0015)
    # Candle 0: High = 100.0
    # Candle 1: Big impulse candle
    # Candle 2: Low = 101.5 (Gap between c0.high 100.0 and c2.low 101.5 is +1.5%)
    klines = [
        {"high": 100.0, "low": 98.0},
        {"high": 105.0, "low": 99.5},
        {"high": 108.0, "low": 101.5},
    ]
    has_fvg, fvg_type, score, reason = detector.detect_latest_fvg(klines)
    assert has_fvg
    assert fvg_type == "BULLISH_FVG"
    assert score >= 70.0
    assert "Bullish FVG" in reason


def test_bearish_fvg_detection():
    detector = FVGDetector(min_gap_pct=0.0015)
    # Candle 0: Low = 100.0
    # Candle 1: Big drop candle
    # Candle 2: High = 98.0 (Gap between c0.low 100.0 and c2.high 98.0 is -2.0%)
    klines = [
        {"high": 102.0, "low": 100.0},
        {"high": 101.0, "low": 96.0},
        {"high": 98.0, "low": 94.0},
    ]
    has_fvg, fvg_type, score, reason = detector.detect_latest_fvg(klines)
    assert has_fvg
    assert fvg_type == "BEARISH_FVG"
    assert "Bearish FVG" in reason


def test_no_fvg_overlapping():
    detector = FVGDetector()
    klines = [
        {"high": 100.0, "low": 95.0},
        {"high": 102.0, "low": 96.0},
        {"high": 101.0, "low": 98.0},  # Low 98 is lower than High 100 (overlaps)
    ]
    has_fvg, fvg_type, score, reason = detector.detect_latest_fvg(klines)
    assert not has_fvg
    assert fvg_type == "NONE"
