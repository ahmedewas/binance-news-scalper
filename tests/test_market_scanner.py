"""Unit tests for MarketScanner."""
from unittest.mock import MagicMock
from src.engine.market_scanner import MarketScanner
from src.core.models import MarketPhase, ScoringResult


def test_market_scanner():
    exchange = MagicMock()
    exchange.get_ticker_price.return_value = 65000.0
    exchange.get_historical_klines.return_value = [{"open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 100}]

    regime = MagicMock()
    regime.detect_phase.return_value = (MarketPhase.ACCUMULATION, 80.0)

    scoring = MagicMock()
    scoring.evaluate.return_value = ScoringResult(
        symbol="BTC/USDT", phase=MarketPhase.ACCUMULATION, phase_score=80.0,
        momentum_score=80.0, volume_score=80.0, news_score=70.0,
        total_score=77.0, is_approved=True
    )

    scanner = MarketScanner(exchange, regime, scoring)
    results = scanner.scan_if_needed(interval_seconds=0.0)

    assert len(results) > 0
    assert results[0]["symbol"] == "BTC/USDT"
    assert results[0]["approved"] is True
