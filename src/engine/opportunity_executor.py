"""Evaluate a fresh opportunity, recording intent before submitting an order."""
from datetime import datetime, timezone
from src.config import config
from src.core.models import Position


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
        if klines and klines[-1].get("close_time") and now.timestamp()*1000 - klines[-1]["close_time"] > 180000:
            return False

        def _reject_early(phase_name, reason_msg):
            latest_news.append({"symbol": item.symbol, "title": item.title, "score": 0.0, "approved": False,
                                "phase": phase_name, "reason": reason_msg, "published_at": published.isoformat()})
            del latest_news[:-30]
            return False

        # 1. Bitcoin Market Gate Veto
        if not item.symbol.startswith("BTC"):
            btc_kl = exchange.get_historical_klines("BTC/USDT", "1m", 6)
            from src.core.btc_gate import BitcoinMarketGate
            is_btc_safe, btc_reason = BitcoinMarketGate().evaluate(btc_kl)
            if not is_btc_safe:
                return _reject_early("BTC_VETO", btc_reason)

        # 2. Multi-Timeframe 15m Alignment Veto
        kl_15m = exchange.get_historical_klines(item.symbol, "15m", 25)
        if kl_15m:
            from src.core.mtf_confluence import MultiTimeframeConfluence
            aligned, mtf_msg = MultiTimeframeConfluence().check_higher_timeframe(kl_15m)
            if not aligned:
                return _reject_early("MTF_VETO", mtf_msg)

        # 3. Cooldown Veto
        if hasattr(exchange, "_cooldown_mgr"):
            cooling, rem = exchange._cooldown_mgr.is_in_cooldown(item.symbol)
            if cooling:
                return _reject_early("COOLDOWN", f"فترة تهدئة ({rem}د)")

        phase, phase_score = regime_detector.detect_phase(klines)
        result = scoring_engine.evaluate(item.symbol, phase, phase_score, klines, item.sentiment_score)
        entry = {"symbol": item.symbol, "title": item.title, "score": result.total_score,
                 "approved": result.is_approved, "phase": phase.value,
                 "reason": result.rejection_reason or "تجاوز فحص الإشارة", "published_at": published.isoformat()}
        latest_news.append(entry)
        del latest_news[:-30]
        if not result.is_approved:
            return False

        # 4. Anti-Slippage Shield
        cur_p = exchange.get_ticker_price(item.symbol)
        if cur_p > 0 and klines:
            from src.exchange.slippage_guard import SlippageGuard
            ok_slip, msg_slip, _ = SlippageGuard().validate_buy_slippage(item.symbol, float(klines[-1]["close"]), cur_p)
            if not ok_slip:
                entry.update(approved=False, reason=msg_slip)
                return False

        rules = exchange.get_market_rules(item.symbol)
        minimum = max(config.min_notional, rules.get("min_notional", 0))
        if slot_size < minimum or slot_size > exchange.get_balance("USDT"):
            entry.update(approved=False, reason="الرصيد أو حجم الصفقة لا يحقق حدود السوق")
            return False

        client_id = before_order(item.symbol, "BUY", slot_size) if before_order else None
        kw = {"client_order_id": client_id} if client_id else {}
        order = exchange.place_market_buy(item.symbol, slot_size, **kw)
        if order.success and order.price > 0 and order.amount > 0:
            positions[item.symbol] = Position(
                symbol=item.symbol, entry_price=order.price, current_price=order.price,
                amount=order.amount, highest_price=order.price, entry_time=now, slot_id=slot_id,
                entry_volume=float(klines[-1]["volume"]), cost_basis=(order.cost + order.fee_quote) if order.cost > 0 else slot_size,
            )
        else:
            entry.update(approved=False, reason=order.message or order.status)
        if after_order:
            after_order(client_id, order)
        if order.success and item.symbol in positions:
            from src.core.atr_calculator import ATRCalculator
            tp_pct, sl_pct, _ = ATRCalculator().calculate_targets(order.price, klines)
            pos_dict = {"symbol": item.symbol, "entry_price": order.price, "cost_basis": slot_size,
                        "target_tp": round(order.price * (1 + tp_pct), 4),
                        "stop_loss": round(order.price * (1 - sl_pct), 4), "slot_id": slot_id}
            if journal:
                journal.log_trade_opened(pos_dict, item.title, result.total_score, phase.value)
            if hasattr(exchange, "_notifier"):
                exchange._notifier.notify_trade_opened(pos_dict, item.title, result.total_score)
            return True
        return False
