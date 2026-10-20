"""Live Order Operations: Execution parsing, submission, and reconciliation."""
import logging
import math
import uuid
import ccxt
from src.core.models import OrderResult

logger = logging.getLogger("LiveExchange")


class LiveOrderMixin:
    def _parse_fees(self, order: dict, symbol: str) -> tuple[float, float, bool]:
        if not order.get("fees") and not order.get("fee"):
            return 0.0, 0.0, False
        fees = order.get("fees") or ([order["fee"]] if order.get("fee") else [])
        market = self.client.market(symbol)
        base, quote = market["base"], market["quote"]
        fee_b = fee_q = 0.0
        for fee in fees:
            val = float(fee.get("cost") or 0)
            if not math.isfinite(val) or val < 0:
                return 0.0, 0.0, False
            if not val:
                continue
            curr = fee.get("currency")
            if curr == base:
                fee_b += val
            elif curr == quote:
                fee_q += val
            else:
                conv = self.get_ticker_price(f"{curr}/{quote}")
                if conv <= 0:
                    return 0.0, 0.0, False
                fee_q += val * conv
        return fee_b, fee_q, True

    def _result(self, symbol: str, side: str, order: dict) -> OrderResult:
        oid = str(order.get("id") or "")
        def unk(msg: str) -> OrderResult:
            return OrderResult(False, oid, symbol, 0, 0, side, "UNKNOWN", msg)
        status, filled = str(order.get("status") or "").lower(), float(order.get("filled") or 0)
        if status not in {"closed", "canceled", "cancelled", "expired", "rejected"}:
            return unk("Order is not terminal; reconciliation required")
        if not math.isfinite(filled) or filled < 0:
            return unk("Invalid executed quantity")
        if filled == 0:
            return OrderResult(False, oid, symbol, 0, 0, side, "REJECTED", "No executed quantity")
        cost = float(order.get("cost") or 0)
        price = float(order.get("average") or (cost / filled if cost > 0 else 0))
        if not math.isfinite(price) or price <= 0:
            return unk("Execution price unavailable")
        cost = cost if cost > 0 else filled * price
        if not math.isfinite(cost):
            return unk("Invalid executed cost")
        fee_b, fee_q, fee_ok = self._parse_fees(order, symbol)
        if not fee_ok:
            return unk("Execution fees unavailable or invalid; reconciliation required")
        amt = filled - fee_b if side == "BUY" else filled
        if amt <= 0:
            return unk("Invalid net execution quantity")
        return OrderResult(True, oid, symbol, price, amt, side, "FILLED", "Confirmed execution", cost, fee_q, fee_b)

    def _submit(self, symbol: str, side: str, quantity: float, client_order_id=None) -> OrderResult:
        if not math.isfinite(quantity) or quantity <= 0:
            return OrderResult(False, "", symbol, 0, 0, side, "REJECTED", "Invalid quantity")
        try:
            rules, price = self.get_market_rules(symbol), self.get_ticker_price(symbol)
            if price <= 0:
                raise ValueError("Fresh price unavailable")
            qty = self.normalize_amount(symbol, quantity) if side == "SELL" else quantity
            amount = qty if side == "SELL" else qty / price
            notional = qty * price if side == "SELL" else qty
            if qty <= 0 or amount < rules["min_amount"] or notional < rules["min_notional"]:
                raise ValueError("Order below market minimum")
        except Exception as exc:
            return OrderResult(False, "", symbol, 0, 0, side, "REJECTED", str(exc))
        cid = client_order_id or "scalper_" + uuid.uuid4().hex[:24]
        try:
            params = {"newClientOrderId": cid}
            order = self.client.create_order(symbol, "market", "buy", None, None, {"quoteOrderQty": qty, **params}) if side == "BUY" else self.client.create_order(symbol, "market", "sell", qty, None, params)
            res = self._result(symbol, side, order)
            res.client_order_id = cid
            return res
        except (ccxt.InsufficientFunds, ccxt.InvalidOrder, ccxt.AuthenticationError) as exc:
            return OrderResult(False, cid, symbol, 0, 0, side, "REJECTED", str(exc))
        except Exception:
            logger.error("Uncertain %s execution for %s; client id %s", side, symbol, cid)
            return OrderResult(False, cid, symbol, 0, 0, side, "UNKNOWN", "Execution uncertain; reconcile order before retrying", client_order_id=cid)

    def reconcile_order(self, symbol: str, client_order_id: str) -> OrderResult:
        try:
            order = self.client.fetch_order(None, symbol, {"origClientOrderId": client_order_id})
            if float(order.get("filled") or 0) > 0 and not order.get("fees") and not order.get("fee"):
                trades = [t for t in self.client.fetch_my_trades(symbol, params={"orderId": order["id"]}) if str(t.get("order")) == str(order["id"])]
                if not math.isclose(sum(float(t.get("amount") or 0) for t in trades), float(order["filled"]), rel_tol=1e-9, abs_tol=1e-12):
                    raise ValueError("Incomplete trade history")
                order["fees"] = [f for t in trades for f in (t.get("fees") or ([t["fee"]] if t.get("fee") else []))]
            res = self._result(symbol, str(order.get("side") or "").upper(), order)
            res.client_order_id = client_order_id
            return res
        except Exception:
            return OrderResult(False, client_order_id, symbol, 0, 0, "", "UNKNOWN", "Reconciliation incomplete", client_order_id=client_order_id)
