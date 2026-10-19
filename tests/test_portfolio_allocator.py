"""Unit tests for Dynamic Portfolio Slot Allocator."""
from src.core.portfolio_allocator import PortfolioAllocator


def test_insufficient_balance():
    allocator = PortfolioAllocator(min_notional=5.0, max_slots=5)
    res = allocator.calculate_slots(4.5)
    assert not res["can_trade"]
    assert res["total_slots"] == 0
    assert res["slot_size"] == 0.0


def test_ten_dollars_two_slots():
    allocator = PortfolioAllocator(min_notional=5.0, max_slots=5)
    res = allocator.calculate_slots(10.0)
    assert res["can_trade"]
    assert res["total_slots"] == 2
    assert res["slot_size"] == 5.0


def test_fifteen_dollars_three_slots():
    allocator = PortfolioAllocator(min_notional=5.0, max_slots=5)
    res = allocator.calculate_slots(15.0)
    assert res["can_trade"]
    assert res["total_slots"] == 3
    assert res["slot_size"] == 5.0


def test_scaling_and_max_cap():
    allocator = PortfolioAllocator(min_notional=5.0, max_slots=5)
    res = allocator.calculate_slots(100.0)
    assert res["can_trade"]
    assert res["total_slots"] == 5
    assert res["slot_size"] == 20.0


def test_slot_assignment():
    allocator = PortfolioAllocator(min_notional=5.0, max_slots=3)
    active = {1, 2}
    avail = allocator.get_available_slot(3, active)
    assert avail == 3

    active_full = {1, 2, 3}
    avail_full = allocator.get_available_slot(3, active_full)
    assert avail_full == -1

    # Test Breakeven Velocity Unlock: slot 1 is zero-risk locked
    unlocked = allocator.get_available_slot(3, active_full, breakeven_locked_ids={1})
    assert unlocked == 101  # Virtual velocity slot unlocked

