"""Unit tests for Symbol Cooldown Manager."""
from src.core.cooldown_manager import CooldownManager


def test_cooldown_manager_flow():
    mgr = CooldownManager(default_cooldown_minutes=15.0)
    assert mgr.is_in_cooldown("SOL/USDT")[0] is False

    mgr.set_cooldown("SOL/USDT", custom_minutes=10.0)
    is_cool, rem = mgr.is_in_cooldown("SOL/USDT")
    assert is_cool is True
    assert 9.0 <= rem <= 10.0

    # Expired cooldown
    mgr.set_cooldown("BTC/USDT", custom_minutes=-1.0)
    is_cool_btc, _ = mgr.is_in_cooldown("BTC/USDT")
    assert is_cool_btc is False


def test_cooldown_clear():
    mgr = CooldownManager()
    mgr.set_cooldown("ETH/USDT", custom_minutes=5.0)
    assert mgr.is_in_cooldown("ETH/USDT")[0] is True
    mgr.clear()
    assert mgr.is_in_cooldown("ETH/USDT")[0] is False
