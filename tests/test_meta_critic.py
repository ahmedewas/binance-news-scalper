"""Unit tests for Meta-Critic Reflection Engine."""
import time
from src.core.meta_critic import MetaCritic


def test_meta_critic_penalty_and_expiry():
    critic = MetaCritic(penalty_duration_sec=100.0)
    now = time.time()

    trades = [
        {"symbol": "SOL/USDT", "pnl_usd": -0.05},
        {"symbol": "SOL/USDT", "pnl_usd": -0.04},
        {"symbol": "BTC/USDT", "pnl_usd": 0.12},
    ]

    summary = critic.reflect_on_history(trades, now=now)
    assert "SOL/USDT" in summary

    # SOL should be penalized
    permitted, reason = critic.is_symbol_permitted("SOL/USDT", now=now + 10)
    assert permitted is False
    assert "CRITIC_PENALTY" in reason

    # BTC should be permitted
    permitted_btc, _ = critic.is_symbol_permitted("BTC/USDT", now=now + 10)
    assert permitted_btc is True

    # After penalty expires (now + 150s), SOL should be permitted again
    permitted_expired, _ = critic.is_symbol_permitted("SOL/USDT", now=now + 150)
    assert permitted_expired is True
