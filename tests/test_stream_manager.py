"""Unit tests for StreamManager."""
from unittest.mock import MagicMock, patch
from src.news.stream_manager import StreamManager


def test_stream_manager_manual_update():
    sm = StreamManager(refresh_interval_seconds=1.0)
    assert sm.get_price("BTC/USDT") is None

    sm.update_price("BTC/USDT", 68500.0)
    assert sm.get_price("BTC/USDT") == 68500.0
    assert sm.get_price("BTCUSDT") == 68500.0


@patch("requests.Session.get")
def test_stream_manager_batch_poll(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [
        {"symbol": "SOLUSDT", "price": "185.50"},
        {"symbol": "BTCUSDT", "price": "67000.00"},
    ]
    mock_get.return_value = mock_resp

    sm = StreamManager(refresh_interval_seconds=0.05)
    sm.start()
    import time
    time.sleep(0.15)

    assert sm.is_active is True
    assert sm.get_price("SOL/USDT") == 185.50
    assert sm.get_price("BTC/USDT") == 67000.00

    sm.stop()
