"""Unit tests for Preemptive Volume Decay Exit Detector."""
from src.core.volume_decay_exit import VolumeDecayExitDetector


def test_volume_decay_exit_trigger():
    detector = VolumeDecayExitDetector(min_retention_ratio=0.25, min_elapsed_minutes=3.0)
    # Entry volume = 1000.0, current volume collapsed to 150.0 (15% retention), elapsed = 4 mins, stagnant PnL
    klines = [{"volume": 150.0} for _ in range(3)]
    should_exit, reason = detector.check_volume_decay(
        entry_volume=1000.0,
        recent_klines=klines,
        elapsed_minutes=4.0,
        current_pnl_pct=0.002,
    )
    assert should_exit
    assert "PREEMPTIVE_VOLUME_DECAY" in reason


def test_volume_healthy_retention_hold():
    detector = VolumeDecayExitDetector(min_retention_ratio=0.25, min_elapsed_minutes=3.0)
    # Entry volume = 1000.0, current volume = 800.0 (80% retention)
    klines = [{"volume": 800.0} for _ in range(3)]
    should_exit, reason = detector.check_volume_decay(
        entry_volume=1000.0,
        recent_klines=klines,
        elapsed_minutes=5.0,
        current_pnl_pct=0.005,
    )
    assert not should_exit
    assert "HOLD" in reason


def test_volume_decay_skipped_when_early():
    detector = VolumeDecayExitDetector(min_elapsed_minutes=3.0)
    # Only 1.5 minutes elapsed -> should not exit yet
    klines = [{"volume": 50.0}]
    should_exit, reason = detector.check_volume_decay(
        entry_volume=1000.0,
        recent_klines=klines,
        elapsed_minutes=1.5,
        current_pnl_pct=0.001,
    )
    assert not should_exit
