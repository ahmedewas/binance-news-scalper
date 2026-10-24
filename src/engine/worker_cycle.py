"""Worker Execution Cycle: position management, candidate evaluation and event loop."""
import time
from datetime import datetime, timezone
from src.config import config
from src.engine.opportunity_executor import OpportunityExecutor


class WorkerCycleMixin:
    def manage_positions(self):
        with self.lock:
            self.stale_symbols.clear()
            for sym, pos in list(self.positions.items()):
                if pos.execution_uncertain: continue
                price = self.exchange.get_ticker_price(sym)
                if price <= 0:
                    self.stale_symbols.add(sym)
                    continue
                if hasattr(self, "shadow_engine"):
                    self.shadow_engine.on_tick(sym, price)
                now = datetime.now(timezone.utc)
                prev_risk = (pos.highest_price, pos.is_breakeven_locked)
                should_exit, reason, ratio = self.risk_manager.evaluate_exit(pos, price, now)
                if prev_risk != (pos.highest_price, pos.is_breakeven_locked):
                    self.persist()
                if not should_exit and config.enable_volume_decay_exit and pos.entry_volume > 0:
                    elapsed = (now - pos.entry_time).total_seconds() / 60
                    if elapsed >= self.volume_decay_detector.min_elapsed:
                        bars = self.exchange.get_historical_klines(sym, '1m', 5)
                        should_exit, reason = self.volume_decay_detector.check_volume_decay(
                            pos.entry_volume, bars, elapsed, (price - pos.entry_price) / pos.entry_price
                        )
                        ratio = 1.0
                if should_exit:
                    self._exit(sym, reason, ratio)

    def _poll_news(self):
        if self.news_future is not None and self.news_future.done():
            try:
                items = self.news_future.result()
                with self.lock:
                    self.candidates.extend(items)
                    self.candidates = self.candidates[-100:]
            except Exception as exc:
                self.error('تعذر تحديث مصادر البيانات: ' + type(exc).__name__)
            self.news_future = None
        if self.news_future is None and time.monotonic() - self.last_news_poll >= 15:
            self.last_news_poll = time.monotonic()
            self.news_future = self.pool.submit(self.news_fetcher.fetch_latest_news)

    def process_news_opportunities(self):
        with self.lock:
            if not self.is_active or self.pending_orders or self.storage_failed or self.stale_symbols:
                return
            now = time.time()
            self.entry_times = [t for t in self.entry_times if now - t < 3600]
            if len(self.entry_times) >= config.max_entries_per_hour:
                return
            eq = self.cash + sum(p.amount * p.current_price for p in self.positions.values())
            alloc = self.allocator.calculate_slots(self.cash, eq)
            slot = self.allocator.get_available_slot(alloc['total_slots'], {p.slot_id for p in self.positions.values()})
            if not alloc['can_trade'] or slot < 0 or len(self.positions) >= self.allocator.max_slots:
                return
            self.candidates.sort(key=lambda x: getattr(x, "sentiment_score", 0.0), reverse=True)
            while self.candidates:
                item = self.candidates.pop(0)
                if item.source == 'binance_spot_flow' and not config.enable_flow_entries:
                    continue
                if item.symbol in self.positions or self.cooldowns.get(item.symbol, 0) > now:
                    continue
                opened = OpportunityExecutor.evaluate_and_open(
                    item, slot, alloc['slot_size'], self.exchange, self.regime_detector, self.scoring_engine,
                    self.positions, self.latest_news, self.journal, before_order=self._before_order, after_order=self._after_order
                )
                if opened:
                    if hasattr(self, "shadow_engine") and item.symbol in self.positions:
                        self.shadow_engine.spawn_shadows(item.symbol, self.positions[item.symbol].entry_price)
                    self.entry_times.append(now)
                    self.cash = self.exchange.get_balance('USDT')
                    self.persist()
                    break
                if self.pending_orders:
                    break

    def step(self):
        try:
            self.manage_positions()
            with self.lock:
                self.cash = self.exchange.get_balance('USDT')
                self._publish()
            self._poll_news()
            self.process_news_opportunities()
            self.last_step = datetime.now(timezone.utc).isoformat()
        except Exception as exc:
            self.is_active = False
            self.error('توقفت الدخولات بعد خطأ: ' + type(exc).__name__)
        finally:
            with self.lock: self._publish()

    def shutdown(self):
        self.pool.shutdown(wait=False, cancel_futures=True)
        with self.lock: self.persist()
