"""Unit tests for SessionAutopsy diagnostic and forensic analysis engine."""
import pytest
from src.core.session_autopsy import SessionAutopsy


def test_empty_session_autopsy():
    report = SessionAutopsy.analyze_session([])
    assert report["total_trades"] == 0
    assert report["win_rate"] == 0.0
    assert report["best_symbol"] == "None"


def test_winning_session_autopsy():
    trades = [
        {"symbol": "SOL/USDT", "pnl_pct": 1.5, "pnl_usd": 0.30, "reason": "ATR_TP"},
        {"symbol": "SOL/USDT", "pnl_pct": 2.0, "pnl_usd": 0.40, "reason": "ATR_TP"},
        {"symbol": "AVAX/USDT", "pnl_pct": -0.8, "pnl_usd": -0.16, "reason": "STOP_LOSS"},
    ]
    report = SessionAutopsy.analyze_session(trades)
    assert report["total_trades"] == 3
    assert report["wins"] == 2
    assert report["losses"] == 1
    assert report["win_rate"] == pytest.approx(66.7, abs=0.1)
    assert report["best_symbol"] == "SOL/USDT"
    assert "استثنائي" in report["recommendation"]


def test_volume_decay_dominant_recommendation():
    trades = [
        {"symbol": "DOT/USDT", "pnl_pct": -0.2, "pnl_usd": -0.04, "reason_arabic": "جفاف أحجام التداول"},
        {"symbol": "NEAR/USDT", "pnl_pct": -0.25, "pnl_usd": -0.05, "reason_arabic": "جفاف أحجام التداول"},
    ]
    report = SessionAutopsy.analyze_session(trades)
    assert report["total_trades"] == 2
    assert report["wins"] == 0
    assert report["losses"] == 2
    assert "الخروج المبكر" in report["recommendation"]
