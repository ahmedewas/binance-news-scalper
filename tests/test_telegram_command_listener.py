"""Unit tests for TelegramCommandListener interactive bot controls."""
from unittest.mock import MagicMock
from src.core.telegram_command_listener import TelegramCommandListener


def test_telegram_listener_unconfigured():
    listener = TelegramCommandListener(None, None, MagicMock())
    assert listener.is_configured is False
    listener.start()
    assert listener.running is False


def test_telegram_listener_status_command():
    worker = MagicMock()
    worker.snapshot.return_value = {
        "mode": "PAPER", "is_active": True, "usdt_balance": 15.0,
        "open_positions": [], "performance": {"win_rate": 60.0, "total_pnl_usd": 1.25}
    }
    listener = TelegramCommandListener("fake_token", "12345", worker)
    reply = listener.handle_command("/status")
    assert "حالة المنظومة" in reply
    assert "PAPER" in reply
    assert "$15.00" in reply


def test_telegram_listener_pause_and_resume():
    worker = MagicMock()
    listener = TelegramCommandListener("fake_token", "12345", worker)

    reply_pause = listener.handle_command("/pause")
    worker.set_active.assert_called_with(False)
    assert "إيقاف" in reply_pause

    reply_resume = listener.handle_command("/resume")
    worker.set_active.assert_called_with(True)
    assert "استئناف" in reply_resume


def test_telegram_listener_close_all():
    worker = MagicMock()
    worker.close_all.return_value = {"status": "ALL_POSITIONS_CLOSED"}
    listener = TelegramCommandListener("fake_token", "12345", worker)

    reply = listener.handle_command("/close_all")
    worker.close_all.assert_called_once()
    assert "ALL_POSITIONS_CLOSED" in reply


def test_telegram_listener_autopsy_and_help():
    worker = MagicMock()
    worker.trade_history = []
    listener = TelegramCommandListener("fake_token", "12345", worker)

    reply_autopsy = listener.handle_command("/autopsy")
    assert "التشريح الجنائي" in reply_autopsy

    reply_help = listener.handle_command("/unknown")
    assert "/status" in reply_help
