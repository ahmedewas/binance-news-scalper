"""Evaluate a fresh opportunity, recording intent before submitting an order."""
from datetime import datetime, timezone
from src.config import config
from src.core.models import Position
from src.core.atr_calculator import ATRCalculator
from src.engine.opportunity_filters import OpportunityFilters


class OpportunityExecutor:
    @staticmethod
    def evaluate_and_open(item, slot_id, slot_size, exchange, regime_detector,
                          scoring_engine, positions, latest_news, journal=None,
                          before_order=None, after_order=None):
        now = datetime.now(timezone.utc)
        published = item.published_at.replace(tzinfo=timezone.utc) if item.published_at.tzinfo is None else item.published_at
        age = (now - published).total_seconds()
        if age < -60 or age > config.max_news_age_seconds:
            return False
        klines = exchange.get_historical_klines(item.symbol, "1m", 40)
        if klines and klines[-1].get("close_time") and now.timestamp() * 1000 - klines[-1]["close_time"] > 180000:
            return False

        def _reject_early(phase_name, reason_msg):
            latest_news.append({"symbol": item.symbol, "title": item.title, "score": 0.0, "approved": False,
                                "phase": phase_name, "reason": reason_msg, "published_at": published.isoformat()})
            del latest_news[:-30]
            return False

        safe_macro, eff_thresh, rej_phase, rej_msg = OpportunityFilters.check_macro_gates(
            item.symbol, exchange, scoring_engine.min_score
        )
        if not safe_macro:
            return _reject_early(rej_phase, rej_msg)

        if hasattr(exchange, "_cooldown_mgr"):
            cooling, rem = exchange._cooldown_mgr.is_in_cooldown(item.symbol)
            if cooling:
                return _reject_early("COOLDOWN", f"فترة تهدئة ({rem}د)")

        phase, phase_score = regime_detector.detect_phase(klines)
        h_score, cvd_score = OpportunityFilters.calculate_alpha_metrics(klines) if klines else (None, None)
        res = scoring_engine.evaluate(item.symbol, phase, phase_score, klines, item.sentiment_score,
                                      cvd_score=cvd_score, hurst_score=h_score)
        approved = res.is_approved and (res.total_score >= eff_thresh)
        rejection = res.rejection_reason or (None if approved else f"Score {res.total_score:.1f} < Adaptive {eff_thresh:.1f}")
        entry = {"symbol": item.symbol, "title": item.title, "score": res.total_score,
                 "approved": approved, "phase": phase.value, "reason": rejection or "تجاوز فحص الإشارة",
                 "published_at": published.isoformat()}
        latest_news.append(entry)
        del latest_news[:-30]
        if not approved:
            return False

        cur_p = exchange.get_ticker_price(item.symbol)
        ok_micro, micro_msg = OpportunityFilters.check_microstructure(item.symbol, klines, cur_p, exchange=exchange)
        if not ok_micro:
            entry.update(approved=False, reason=micro_msg)
            return False

        rules = exchange.get_market_rules(item.symbol)
        minimum = max(config.min_notional, rules.get("min_notional", 0))
        th = getattr(exchange, "_trade_history", None) or []
        s_w = sum(1 for t in th if t.get("symbol") == item.symbol and t.get("pnl_usd", 0) > 0)
        s_l = sum(1 for t in th if t.get("symbol") == item.symbol and t.get("pnl_usd", 0) < 0)
        from src.core.kelly_sizer import KellySizer
        k_mult = KellySizer().calculate_alpha_multiplier(res.total_score, s_w, s_l)
        eff_size = min(round(slot_size * k_mult, 2), exchange.get_balance("USDT"))
        if eff_size < minimum:
            entry.update(approved=False, reason="الرصيد أو حجم الصفقة لا يحقق حدود السوق")
            return False

        client_id = before_order(item.symbol, "BUY", eff_size) if before_order else None
        order = exchange.place_market_buy(item.symbol, eff_size, **({"client_order_id": client_id} if client_id else {}))
        if order.success and order.price > 0 and order.amount > 0:
            tp_pct, sl_pct, _ = ATRCalculator().calculate_targets(order.price, klines)
            target_tp = order.price * (1.0 + tp_pct)
            stop_loss = order.price * (1.0 - sl_pct)
            vol = float(klines[-1]["volume"]) if klines else 1.0
            avg_v = max(1e-5, sum(float(k.get("volume", 0.0)) for k in klines[-10:]) / 10.0) if klines else 1.0
            from src.core.vector_memory import VectorMemoryBuffer
            entry_vec = VectorMemoryBuffer.extract_vector(vol / avg_v, (cvd_score or 50) >= 50, 0.0, h_score or 0.5, phase_score)
            positions[item.symbol] = Position(
                symbol=item.symbol, entry_price=order.price, current_price=order.price,
                amount=order.amount, highest_price=order.price, entry_time=now, slot_id=slot_id,
                entry_volume=float(klines[-1]["volume"]), cost_basis=(order.cost + order.fee_quote) if order.cost > 0 else eff_size,
                target_tp=target_tp, stop_loss=stop_loss, entry_vector=entry_vec,
            )
            pos_dict = {"symbol": item.symbol, "entry_price": order.price, "cost_basis": eff_size,
                        "target_tp": target_tp, "stop_loss": stop_loss, "slot_id": slot_id}
            if journal:
                journal.log_trade_opened(pos_dict, item.title, res.total_score, phase.value)
            if hasattr(exchange, "_notifier"):
                exchange._notifier.notify_trade_opened(pos_dict, item.title, res.total_score)
        else:
            entry.update(approved=False, reason=order.message or order.status)
        if after_order:
            after_order(client_id, order)
        return order.success and (item.symbol in positions)
