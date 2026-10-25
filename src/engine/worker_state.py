"""Persistent state helpers; the worker is the sole owner of mutations."""
from dataclasses import asdict
from datetime import datetime, timezone
from src.core.models import Position


class WorkerState:
    def persist(self):
        if self.store is None:
            return
        positions = []
        for p in self.positions.values():
            row = asdict(p)
            row['entry_time'] = p.entry_time.isoformat()
            positions.append(row)
        tracker_trades = [{**t, 'timestamp': t['timestamp'].isoformat()} for t in self.tracker.trades]
        state = dict(version=1, mode=self.mode, positions=positions,
                     trade_history=self.trade_history, pending_orders=self.pending_orders,
                     is_active=self.is_active, initial_balance=self.tracker.initial_balance,
                     start_time=self.tracker.start_time.isoformat(), tracker_trades=tracker_trades,
                     hourly_snapshots=self.tracker.hourly_snapshots,
                     last_snapshot_hour=self.tracker._last_snapshot_hour,
                     cooldowns=self.cooldowns, entry_times=self.entry_times,
                     loss_limit_hit=self.loss_limit_hit)
        if self.mode == 'PAPER':
            state['paper'] = dict(usdt_balance=self.exchange.usdt_balance,
                                  holdings=self.exchange.holdings)
        try:
            self.store.save(state)
        except Exception:
            self.is_active = False
            self.storage_failed = True
            self.last_error = 'تعذر حفظ حالة التداول؛ أوقفت الأوامر الجديدة لحماية تسوية الصفقات'
            raise

    def restore(self):
        if self.store is None:
            return
        state = self.store.load()
        if not state:
            return
        if state['mode'] != self.mode:
            raise ValueError('State mode mismatch')
        for row in state['positions']:
            row = dict(row)
            row['entry_time'] = datetime.fromisoformat(row['entry_time'])
            pos = Position(**row)
            self.positions[pos.symbol] = pos
        self.trade_history = state.get('trade_history', [])
        self.pending_orders = state.get('pending_orders', {})
        self.cooldowns = state.get('cooldowns', {})
        self.entry_times = state.get('entry_times', [])
        self.loss_limit_hit = self.mode == 'LIVE' and state.get('loss_limit_hit', False)
        self.tracker.initial_balance = state['initial_balance']
        if not self.trade_history and not self.positions:
            self.tracker.start_time = datetime.now(timezone.utc)
        elif state.get('start_time'):
            self.tracker.start_time = datetime.fromisoformat(state['start_time'])
        self.tracker.trades = [{**t, 'timestamp': datetime.fromisoformat(t['timestamp'])}
                               for t in state.get('tracker_trades', [])]
        self.tracker.hourly_snapshots = state.get('hourly_snapshots', [])
        self.tracker._last_snapshot_hour = state.get('last_snapshot_hour', 0)
        if self.mode == 'PAPER':
            self.exchange.usdt_balance = state['paper']['usdt_balance']
            self.exchange.holdings = state['paper']['holdings']
        self.is_active = bool(state.get('is_active')) and self.mode == 'PAPER'
        if self.pending_orders or self.loss_limit_hit:
            self.is_active = False
        for intent in self.pending_orders.values():
            if intent['symbol'] in self.positions:
                self.positions[intent['symbol']].execution_uncertain = True
