"""Unit tests for TelegramNotifier asynchronous trade alert engine."""
from unittest.mock import patch, MagicMock
from src.core.telegram_notifier import TelegramNotifier


def test_telegram_notifier_unconfigured():
    notifier = TelegramNotifier(None, None)
    assert notifier.is_configured is False
    # Calling notifications should be silent no-op
    notifier.notify_trade_opened({"symbol": "SOL/USDT", "entry_price": 100}, "Test", 85.0)
    notifier.notify_trade_closed({"symbol": "SOL/USDT", "pnl_pct": 1.5, "pnl_usd": 0.3}, 100.0)


@patch("requests.post")
def test_telegram_notifier_configured(mock_post):
    mock_post.return_value = MagicMock(status_code=200)
    notifier = TelegramNotifier("fake_token", "fake_chat")
    assert notifier.is_configured is True

    # Send opened alert
    pos = {"symbol": "BTC/USDT", "entry_price": 65000, "target_tp": 66000, "stop_loss": 64500}
    notifier.notify_trade_opened(pos, "Breakout", 88.0)

    # Send closed alert
    trade = {"symbol": "BTC/USDT", "pnl_pct": 1.2, "pnl_usd": 15.0, "duration_mins": 8, "reason": "ATR_TP"}
    notifier.notify_trade_closed(trade, 1015.0)
