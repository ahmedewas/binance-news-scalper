"""Apply confirmed executions to positions and their remaining cost basis."""
import logging, math
from datetime import datetime, timezone
from typing import Dict, List, Any
from src.core.models import Position
from src.exchange.base import BaseExchange
from src.core.performance_tracker import PerformanceTracker

logger = logging.getLogger("PositionHandler")


class PositionHandler:
    @staticmethod
    def execute_exit(exchange: BaseExchange, positions: Dict[str, Position],
                     symbol: str, reason: str, exit_ratio: float,
                     trade_history: List[Dict[str, Any]], client_order_id=None) -> Dict[str, Any]:
        def res_dict(ok, msg, status="REJECTED", **ext):
            return dict(success=ok, symbol=symbol, message=msg, status=status, **ext)
        pos = positions.get(symbol)
        if pos is None:
            return res_dict(False, "Position not found")
        if pos.execution_uncertain:
            return res_dict(False, "Reconcile uncertain execution before retrying", "UNKNOWN")
        if not math.isfinite(exit_ratio) or not 0 < exit_ratio <= 1 or not math.isfinite(pos.amount) or pos.amount <= 0:
            return res_dict(False, "Invalid exit ratio or position")

        epsilon = max(1e-12, pos.amount * 1e-12)
        try:
            price = exchange.get_ticker_price(symbol)
            if not math.isfinite(price) or price <= 0:
                return res_dict(False, "Fresh price unavailable")
            rules = exchange.get_market_rules(symbol) if hasattr(exchange, "get_market_rules") else {}
            normalize = getattr(exchange, "normalize_amount", lambda s, q: q)
            qty = normalize(symbol, pos.amount * exit_ratio)
            def ok_val(q):
                return q > epsilon and q >= rules.get("min_amount", 0) and q * price >= rules.get("min_notional", 0)
            if exit_ratio < 1 and (not ok_val(qty) or not ok_val(normalize(symbol, pos.amount - qty))):
                qty = normalize(symbol, pos.amount)
            if not ok_val(qty):
                return res_dict(False, "Remaining position below market minimum")
            kw = {"client_order_id": client_order_id} if client_order_id else {}
            res = exchange.place_market_sell(symbol, qty, **kw)
        except Exception as exc:
            pos.execution_uncertain = True
            logger.exception("Uncertain exit for %s: %s", symbol, exc)
            return res_dict(False, "Exit uncertain; reconciliation required", "UNKNOWN")

        if not res.success:
            if res.status == "UNKNOWN":
                pos.execution_uncertain = True
            return res_dict(False, res.message, res.status, order_id=res.order_id)
        return PositionHandler.apply_fill(positions, symbol, reason, res, trade_history, exchange)

    @staticmethod
    def apply_fill(positions, symbol, reason, res, trade_history, exchange=None):
        def res_dict(ok, msg, status="UNKNOWN", **ext):
            return dict(success=ok, symbol=symbol, message=msg, status=status, **ext)
        pos = positions.get(symbol)
        if pos is None:
            return res_dict(False, "Position missing during reconciliation")
        if any(t.get("order_id") == res.order_id for t in trade_history if res.order_id):
            return res_dict(False, "Execution already recorded")

        epsilon = max(1e-12, pos.amount * 1e-12)
        fee_b, fee_q, cost = getattr(res, "fee_base", 0.0), getattr(res, "fee_quote", 0.0), getattr(res, "cost", 0.0)
        removed = res.amount + fee_b
        if (not all(math.isfinite(v) for v in (res.amount, res.price, removed, cost, fee_q))
                or res.amount <= 0 or res.price <= 0 or removed > pos.amount + epsilon
                or removed <= 0 or fee_q < 0 or fee_b < 0 or cost < 0):
            pos.execution_uncertain = True
            return res_dict(False, "Invalid fill; reconciliation required", "UNKNOWN", order_id=res.order_id)

        removed = min(removed, pos.amount)
        basis = pos.cost_basis if pos.cost_basis > 0 else pos.entry_price * pos.amount
        sold_basis = basis * removed / pos.amount
        proceeds = (cost if cost > 0 else res.amount * res.price) - fee_q
        pnl_usd = proceeds - sold_basis
        pnl_pct = pnl_usd / sold_basis * 100 if sold_basis > 0 else 0.0
        now = datetime.now(timezone.utc)

        trade = {
            "id": res.order_id, "order_id": res.order_id, "symbol": symbol, "entry_price": pos.entry_price,
            "exit_price": res.price, "amount": res.amount, "cost_basis": sold_basis, "fee_quote": fee_q,
            "fee_base": fee_b, "pnl_pct": round(pnl_pct, 4), "pnl_usd": round(pnl_usd, 8),
            "reason": reason, "reason_arabic": PerformanceTracker.translate_reason(reason),
            "duration_mins": round((now - pos.entry_time).total_seconds() / 60, 1),
            "ratio": removed / pos.amount, "timestamp": now.isoformat(),
        }
        pos.amount, pos.cost_basis, pos.execution_uncertain = max(0.0, pos.amount - removed), max(0.0, basis - sold_basis), False
        if "PARTIAL_TP" in reason:
            pos.partial_tp_done = True
        if pos.amount <= epsilon:
            del positions[symbol]
            if exchange and hasattr(exchange, "_cooldown_mgr"):
                exchange._cooldown_mgr.set_cooldown(symbol, 15.0)
            if exchange and hasattr(exchange, "_notifier"):
                exchange._notifier.notify_trade_closed(trade, getattr(exchange, "usdt_balance", 0.0))
        trade_history.append(trade)
        return res_dict(True, "Confirmed exit", res.status, trade=trade, order_id=res.order_id)
