"""Unit tests for Wyckoff Volume Exhaustion and Whale Absorption Detector."""
from src.core.volume_exhaustion import VolumeExhaustionDetector


def test_wyckoff_spring_absorption_wick():
    detector = VolumeExhaustionDetector(min_wick_ratio=0.40, min_vol_multiplier=1.6)
    # 9 background candles with volume 100
    klines = [{"open": 10.0, "high": 10.5, "low": 9.5, "close": 10.2, "volume": 100.0} for _ in range(9)]
    # 10th candle: Massive volume (300) with a long lower wick (spring):
    # low = 8.0, open = 9.8, close = 10.0, high = 10.2 -> range = 2.2, lower wick = 9.8 - 8.0 = 1.8 (81.8% wick)
    spring_candle = {
        "open": 9.8, "high": 10.2, "low": 8.0, "close": 10.0, "volume": 350.0
    }
    klines.append(spring_candle)

    has_abs, abs_type, score, reason = detector.analyze_absorption(klines)
    assert has_abs
    assert abs_type == "WYCKOFF_SPRING"
    assert score >= 75.0
    assert "Whale Absorption Wick" in reason


def test_wyckoff_upthrust_distribution_wick():
    detector = VolumeExhaustionDetector(min_wick_ratio=0.40, min_vol_multiplier=1.6)
    klines = [{"open": 10.0, "high": 10.5, "low": 9.5, "close": 10.2, "volume": 100.0} for _ in range(9)]
    # Upthrust candle: Huge upper wick with heavy volume
    # low = 9.8, open = 10.0, close = 10.1, high = 12.0 -> range = 2.2, upper wick = 12.0 - 10.1 = 1.9 (86.3% wick)
    utad_candle = {
        "open": 10.0, "high": 12.0, "low": 9.8, "close": 10.1, "volume": 300.0
    }
    klines.append(utad_candle)

    has_abs, abs_type, score, reason = detector.analyze_absorption(klines)
    assert has_abs
    assert abs_type == "WYCKOFF_UPTHRUST"
    assert "Distribution Upthrust" in reason
