"""Unit tests for Universe Manager."""
from unittest.mock import MagicMock
from src.engine.universe_manager import UniverseManager


def test_universe_manager_fallback():
    mgr = UniverseManager()
    symbols = mgr.get_symbols()
    assert len(symbols) >= 10
    assert "BTC/USDT" in symbols
    assert "SOL/USDT" in symbols


def test_universe_manager_filter():
    mgr = UniverseManager(min_quote_volume=100000.0)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [
        {"symbol": "BTCUSDT", "quoteVolume": "50000000.0"},
        {"symbol": "ETHUSDT", "quoteVolume": "30000000.0"},
        {"symbol": "BTCUPUSDT", "quoteVolume": "99999999.0"},  # Leveraged, should be excluded
        {"symbol": "DEADCOINUSDT", "quoteVolume": "100.0"},  # Low volume, excluded
    ]
    mgr.session.get = MagicMock(return_value=mock_resp)
    res = mgr.refresh_universe()
    assert "BTC/USDT" in res
    assert "ETH/USDT" in res
    assert not any("UP" in s for s in res)
