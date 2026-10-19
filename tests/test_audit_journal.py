"""Unit tests for AuditJournal."""
import os
import tempfile
from src.core.audit_journal import AuditJournal


def test_audit_journal():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "TEST_JOURNAL.md")
        journal = AuditJournal(file_path=path)

        assert os.path.exists(path)
        content = journal.read_journal()
        assert "سجل التدقيق" in content

        # Log open
        journal.log_trade_opened(
            {"symbol": "SOL/USDT", "entry_price": 180.5, "cost_basis": 5.0, "target_tp": 182.5, "stop_loss": 178.5, "slot_id": 1},
            "Solana Launchpool listing catalyst", 88.5, "ACCUMULATION"
        )
        content2 = journal.read_journal()
        assert "SOL/USDT" in content2
        assert "180.5" in content2
        assert "binance.com/en/trade/SOL_USDT" in content2

        # Log close
        journal.log_trade_closed(
            {"symbol": "SOL/USDT", "pnl_pct": 1.2, "pnl_usd": 0.06, "entry_price": 180.5, "exit_price": 182.66, "duration_mins": 8.5, "reason_arabic": "جني أرباح متحرك"},
            balance_after=15.06
        )
        content3 = journal.read_journal()
        assert "إغلاق صفقة" in content3
        assert "+1.2%" in content3
        assert "15.06" in content3
