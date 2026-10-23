"""Tests for EcosystemRegistry and SectorLeaderGate."""
import pytest
from src.core.ecosystem_registry import EcosystemRegistry
from src.core.sector_gate import SectorLeaderGate


class MockExchange:
    def __init__(self, klines_map=None):
        self.klines_map = klines_map or {}

    def get_historical_klines(self, symbol, interval, limit):
        return self.klines_map.get(symbol, [])


def test_ecosystem_registry_mapping():
    assert EcosystemRegistry.get_pillar_for_symbol("JTO/USDT") == "SOLANA"
    assert EcosystemRegistry.get_leader_for_symbol("JTO/USDT") == "SOL/USDT"
    assert EcosystemRegistry.is_leader("SOL/USDT") is True
    assert EcosystemRegistry.is_leader("JTO/USDT") is False
    assert "TAO/USDT" in EcosystemRegistry.get_all_symbols()
    assert EcosystemRegistry.get_pillar_for_symbol("UNKNOWN/USDT") is None


def test_sector_gate_leader_self():
    gate = SectorLeaderGate()
    ex = MockExchange()
    safe, msg, bonus = gate.evaluate_sector("SOL/USDT", ex)
    assert safe is True
    assert msg == "LEADER_SELF_OR_UNTRACKED"
    assert bonus == 0.0


def test_sector_gate_leader_dump():
    gate = SectorLeaderGate()
    # SOL dumps from 100 to 99 (-1.0% > 0.6% threshold)
    kl = [
        {"close": 100.0, "open": 100.0, "volume": 10.0},
        {"close": 99.5, "open": 100.0, "volume": 10.0},
        {"close": 99.0, "open": 99.5, "volume": 15.0},
    ]
    ex = MockExchange({"SOL/USDT": kl})
    safe, msg, bonus = gate.evaluate_sector("JTO/USDT", ex)
    assert safe is False
    assert "SECTOR_LEADER_DUMP" in msg
    assert bonus == 0.0


def test_sector_gate_leader_surge_bonus():
    gate = SectorLeaderGate()
    # SOL pumps from 100 to 101.5 (+1.5% > 0.8% threshold)
    kl = [
        {"close": 100.0, "open": 100.0, "volume": 10.0},
        {"close": 100.5, "open": 100.0, "volume": 10.0},
        {"close": 101.5, "open": 100.5, "volume": 15.0},
    ]
    ex = MockExchange({"SOL/USDT": kl})
    safe, msg, bonus = gate.evaluate_sector("JTO/USDT", ex)
    assert safe is True
    assert "SECTOR_LEADER_SURGE" in msg
    assert bonus > 0.0
