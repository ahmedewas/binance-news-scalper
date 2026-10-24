"""Unit tests for Counterfactual Shadow Engine."""
from src.core.shadow_engine import ShadowEngine


def test_shadow_engine_lifecycle():
    engine = ShadowEngine()
    engine.spawn_shadows("APT/USDT", 10.0)

    # 1. Price jumps to 10.10 (+1.0%)
    # SCALP_FAST target is +0.9%, should hit TP
    engine.on_tick("APT/USDT", 10.10)
    assert engine.active_shadows["APT/USDT"]["SCALP_FAST"].is_closed is True
    assert engine.active_shadows["APT/USDT"]["SCALP_FAST"].exit_reason == "SHADOW_TP"
    assert engine.active_shadows["APT/USDT"]["MOMENTUM_MID"].is_closed is False

    # 2. Price jumps further to 10.15 (+1.5%)
    # MOMENTUM_MID target is +1.4%, should hit TP
    engine.on_tick("APT/USDT", 10.15)
    assert engine.active_shadows["APT/USDT"]["MOMENTUM_MID"].is_closed is True

    # 3. Evaluate regret against actual trade that made only +0.005 (+0.5%)
    best, regret, pnls = engine.evaluate_regret("APT/USDT", actual_pnl_pct=0.005)
    assert "MOMENTUM_MID" in best
    assert regret > 0.0
    assert "APT/USDT" not in engine.active_shadows
