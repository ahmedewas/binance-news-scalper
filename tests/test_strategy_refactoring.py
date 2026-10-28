"""Tests verifying pullback entry logic, decoupled scoring filters, and widened risk targets."""
from datetime import datetime, timezone
import pytest
from src.core.atr_calculator import ATRCalculator
from src.engine.opportunity_filters import OpportunityFilters
from src.engine.opportunity_executor import OpportunityExecutor
from src.core.models import NewsItem, MarketPhase, ScoringResult
from src.exchange.paper import PaperExchange


def test_atr_calculator_widened_breathing_room():
    calc = ATRCalculator(period=5, tp_multiplier=1.8, sl_multiplier=1.0)
    klines = [{"high": 105.0 + i, "low": 95.0 + i, "close": 100.0 + i} for i in range(10)]
    tp_pct, sl_pct, _ = calc.calculate_targets(100.0, klines)
    assert tp_pct >= 0.012
    assert sl_pct >= 0.008


def test_opportunity_executor_pullback_validation_rejects_spike():
    exchange = PaperExchange(100)
    exchange.get_ticker_price = lambda sym: 105.0  # +5% spike over average of 100.0
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    klines = [{"high": 100.5, "low": 99.5, "close": 100.0, "volume": 100.0, "close_time": now_ms} for _ in range(40)]
    exchange.get_historical_klines = lambda *a, **k: klines
    regime = type("MockRegime", (), {"detect_phase": lambda s, k: (MarketPhase.MARKUP, 85.0)})()
    scoring = type("MockScoring", (), {
        "min_score": 70.0,
        "evaluate": lambda *a, **k: ScoringResult("SOL/USDT", MarketPhase.MARKUP, 85.0, 80.0, 80.0, 80.0, 80.0, True, None)
    })()
    
    latest_news = []
    item = NewsItem("1", "Title", "src", "SOL/USDT", 80.0, datetime.now(timezone.utc))
    opened = OpportunityExecutor.evaluate_and_open(
        item, 1, 20.0, exchange, regime, scoring, {}, latest_news
    )
    assert not opened
    assert len(latest_news) == 1
    assert "تضخم سعري" in latest_news[0]["reason"]


def test_macro_gates_soft_penalty_for_sector():
    exchange = PaperExchange(100)
    exchange.get_historical_klines = lambda *a, **k: []
    safe, eff_thresh, _, _ = OpportunityFilters.check_macro_gates("SOL/USDT", exchange, min_score=70.0)
    assert safe is True
    assert eff_thresh >= 70.0
