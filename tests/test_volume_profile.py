"""Unit tests for Volume Profile POC and Value Area Analyzer."""
from src.core.volume_profile import VolumeProfileAnalyzer


def test_volume_profile_poc_and_val():
    analyzer = VolumeProfileAnalyzer(num_bins=10)
    # 20 klines traded mostly around 100.0, with a few spikes to 105
    klines = []
    for _ in range(15):
        klines.append({"open": 99.8, "high": 100.2, "low": 99.7, "close": 100.1, "volume": 1000.0})
    for _ in range(3):
        klines.append({"open": 104.0, "high": 105.0, "low": 103.8, "close": 104.5, "volume": 100.0})

    vp = analyzer.compute_profile(klines)
    assert 99.5 <= vp["poc"] <= 100.5
    assert vp["val"] <= vp["poc"] <= vp["vah"]
    assert vp["total_vol"] > 0


def test_evaluate_entry_edge_near_val():
    analyzer = VolumeProfileAnalyzer()
    klines = [
        {"high": 105.0, "low": 100.0, "close": 102.0, "volume": 100.0},
        {"high": 103.0, "low": 100.0, "close": 101.0, "volume": 500.0},
        {"high": 102.0, "low": 100.0, "close": 100.5, "volume": 800.0},
    ]
    ok, msg, bonus = analyzer.evaluate_entry_edge(100.1, klines)
    assert ok is True
    assert "VALUE_AREA" in msg or "POC" in msg
    assert bonus >= 0


def test_evaluate_entry_edge_overextended_above_vah():
    analyzer = VolumeProfileAnalyzer()
    klines = [
        {"high": 101.0, "low": 100.0, "close": 100.5, "volume": 1000.0},
        {"high": 101.2, "low": 100.1, "close": 100.4, "volume": 1000.0},
    ]
    # Price 106 is 5% above the VAH
    ok, msg, bonus = analyzer.evaluate_entry_edge(106.0, klines)
    assert ok is False
    assert "EXTENDED_ABOVE_VAH" in msg
    assert bonus < 0
