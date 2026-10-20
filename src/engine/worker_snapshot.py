"""Worker Snapshot and Telemetry Publishing: formats positions, metrics and health."""
import copy
from datetime import datetime, timezone
from src.config import config


class WorkerSnapshotMixin:
    def _publish(self):
        now = datetime.now(timezone.utc)
        equity = self.cash + sum(p.amount * p.current_price for p in self.positions.values())
        if equity <= self.tracker.initial_balance * (1 - config.max_session_loss_pct):
            self.loss_limit_hit = True
            self.is_active = False

        rows = []
        for p in self.positions.values():
            elapsed = (now - p.entry_time).total_seconds() / 60
            basis = p.cost_basis or p.entry_price * p.amount
            stop = p.entry_price * (1 - self.risk_manager.stop_loss_pct)
            if p.is_breakeven_locked:
                stop = p.entry_price * (1 + self.risk_manager.fee_coverage_pct)
            if p.highest_price >= p.entry_price * (1 + self.risk_manager.trailing_tp_pct):
                stop = max(stop, p.highest_price * (1 - self.risk_manager.trailing_offset_pct))
            pnl = p.current_price * p.amount - basis
            rows.append(dict(
                symbol=p.symbol, entry_price=p.entry_price, current_price=p.current_price,
                amount=p.amount, cost_basis=basis, pnl_usd=round(pnl, 8), pnl_pct=round(pnl / basis * 100, 4),
                highest_price=p.highest_price, stop_loss=stop,
                target_tp=p.entry_price * (1 + self.risk_manager.stage1_tp_pct),
                is_breakeven_locked=p.is_breakeven_locked, partial_tp_done=p.partial_tp_done,
                elapsed_mins=round(elapsed, 1), remaining_mins=max(0, round(self.risk_manager.timeout_minutes - elapsed, 1)),
                slot_id=p.slot_id, execution_uncertain=p.execution_uncertain,
                price_stale=p.symbol in self.stale_symbols
            ))

        scanner = getattr(self.news_fetcher, 'market_scanner', None)
        status = dict(
            mode=self.mode, is_active=self.is_active, usdt_balance=self.cash, equity=equity,
            allocation=self.allocator.calculate_slots(self.cash, equity), open_positions=rows,
            trade_history=self.trade_history[-500:], latest_news=self.latest_news[-30:],
            performance=self.tracker.get_summary(equity), market_radar=getattr(scanner, 'cached_results', []) or [],
            pending_orders=self.pending_orders, health=dict(
                last_step=self.last_step, last_scan=getattr(scanner, 'last_completed_at', None),
                last_error=self.last_error, errors=self.errors, price_stale=list(self.stale_symbols),
                loss_limit_hit=self.loss_limit_hit
            ),
            settings=dict(
                min_score=self.scoring_engine.min_score, max_slots=self.allocator.max_slots,
                stop_loss_pct=self.risk_manager.stop_loss_pct, trailing_tp_pct=self.risk_manager.trailing_tp_pct,
                timeout_minutes=self.risk_manager.timeout_minutes, max_session_loss_pct=config.max_session_loss_pct,
                enable_flow_entries=config.enable_flow_entries, enable_volume_decay_exit=config.enable_volume_decay_exit,
                max_entries_per_hour=config.max_entries_per_hour, symbol_cooldown_minutes=config.symbol_cooldown_minutes
            )
        )
        with self.snapshot_lock:
            self._snapshot = copy.deepcopy(status)

    def snapshot(self):
        with self.snapshot_lock:
            return copy.deepcopy(self._snapshot)
