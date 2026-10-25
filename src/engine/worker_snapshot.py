"""Worker Snapshot and Telemetry Publishing: formats positions, metrics and health."""
import copy
from datetime import datetime, timezone
from src.config import config


class WorkerSnapshotMixin:
    def _publish(self):
        now = datetime.now(timezone.utc)
        equity = self.cash + sum(p.amount * p.current_price for p in self.positions.values())
        if self.mode == 'PAPER':
            self.loss_limit_hit = False
        elif self.mode == 'LIVE' and equity <= self.tracker.initial_balance * (1 - config.max_session_loss_pct):
            self.loss_limit_hit = True
            self.is_active = False

        rows = []
        for p in self.positions.values():
            elapsed = (now - p.entry_time).total_seconds() / 60
            basis = p.cost_basis or p.entry_price * p.amount
            pnl = p.current_price * p.amount - basis
            target, stop, _ = self.risk_manager.exit_levels(p)
            gain_pct = round((p.current_price - p.entry_price) / p.entry_price * 100, 2)
            peak_pct = round((p.highest_price - p.entry_price) / p.entry_price * 100, 2)
            dist_tp = round((target - p.current_price) / p.current_price * 100, 2)
            dist_sl = round((p.current_price - stop) / p.current_price * 100, 2)
            rows.append(dict(
                symbol=p.symbol, entry_price=p.entry_price, current_price=p.current_price,
                amount=p.amount, cost_basis=basis, pnl_usd=round(pnl, 4), pnl_pct=round(pnl / basis * 100, 2),
                highest_price=p.highest_price, stop_loss=stop, target_tp=target,
                gain_pct=gain_pct, peak_pct=peak_pct, dist_to_tp=dist_tp, dist_to_sl=dist_sl,
                is_breakeven_locked=p.is_breakeven_locked, partial_tp_done=p.partial_tp_done,
                elapsed_mins=round(elapsed, 1), remaining_mins=max(0, round(self.risk_manager.timeout_minutes - elapsed, 1)),
                slot_id=p.slot_id, execution_uncertain=p.execution_uncertain, price_stale=p.symbol in self.stale_symbols
            ))

        scanner = getattr(self.news_fetcher, 'market_scanner', None)
        gen = getattr(self, "genetic_optimizer", None)
        crit = getattr(self, "meta_critic", None)
        vmem = getattr(self, "vector_memory", None)
        fit = getattr(gen, "get_fittest_params", lambda: {})()
        adaptive_ai = dict(
            generation=getattr(gen, "generation", 1),
            fittest_tp=fit.get("tp_pct", self.risk_manager.trailing_tp_pct),
            fittest_sl=fit.get("sl_pct", self.risk_manager.stop_loss_pct),
            fittest_timeout=fit.get("timeout_min", self.risk_manager.timeout_minutes),
            memory_wins=len(getattr(vmem, "win_vectors", [])),
            memory_losses=len(getattr(vmem, "loss_vectors", [])),
            penalized_symbols=list(getattr(crit, "get_penalized_symbols", lambda: set())()),
            critic_summary=getattr(crit, "last_reflection_summary", ""),
        )

        status = dict(
            mode=self.mode, is_active=self.is_active, usdt_balance=self.cash, equity=equity,
            allocation=self.allocator.calculate_slots(self.cash, equity), open_positions=rows,
            trade_history=self.trade_history[-500:], latest_news=self.latest_news[-30:],
            performance=self.tracker.get_summary(equity), market_radar=getattr(scanner, 'cached_results', []) or [],
            pending_orders=self.pending_orders, adaptive_ai=adaptive_ai, health=dict(
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
        with self.snapshot_lock: self._snapshot = copy.deepcopy(status)

    def snapshot(self):
        with self.snapshot_lock: return copy.deepcopy(self._snapshot)
