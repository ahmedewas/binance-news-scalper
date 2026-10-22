"""Trading owner: serialize execution, persist intents and expose cached status."""
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from src.config import config
from src.core.audit_journal import AuditJournal
from src.core.cooldown_manager import CooldownManager
from src.core.performance_tracker import PerformanceTracker
from src.core.telegram_notifier import TelegramNotifier
from src.core.volume_decay_exit import VolumeDecayExitDetector
from src.engine.worker_admin import WorkerAdminMixin
from src.engine.worker_cycle import WorkerCycleMixin
from src.engine.worker_order_ops import WorkerOrderOpsMixin
from src.engine.worker_snapshot import WorkerSnapshotMixin
from src.engine.worker_state import WorkerState


class BotWorker(WorkerSnapshotMixin, WorkerOrderOpsMixin, WorkerCycleMixin, WorkerAdminMixin, WorkerState):
    def __init__(self, exchange, allocator, regime_detector, scoring_engine,
                 risk_manager, news_fetcher, store=None, journal=None, mode=None):
        self.exchange, self.allocator = exchange, allocator
        self.regime_detector, self.scoring_engine = regime_detector, scoring_engine
        self.risk_manager, self.news_fetcher = risk_manager, news_fetcher
        self.mode = mode or config.trading_mode
        self.store = store
        self.lock = threading.RLock()
        self.snapshot_lock = threading.Lock()
        self.positions, self.pending_orders, self.cooldowns = {}, {}, {}
        self.trade_history, self.latest_news, self.entry_times, self.candidates = [], [], [], []
        self.last_error, self.last_step, self.errors = '', None, []
        self.stale_symbols = set()
        self.loss_limit_hit = self.storage_failed = False
        self.is_active = self.mode == 'PAPER'
        self.cash = float(exchange.get_balance('USDT'))
        self.tracker = PerformanceTracker(max(self.cash, 0.01))
        self.journal = journal if journal is not None else AuditJournal()
        self.volume_decay_detector = VolumeDecayExitDetector(min_retention_ratio=0.10, min_elapsed_minutes=14.0)
        self.cooldown_mgr = CooldownManager(default_cooldown_minutes=15.0)
        self.exchange._cooldown_mgr = self.cooldown_mgr
        self.notifier = TelegramNotifier(getattr(config, "telegram_bot_token", None), getattr(config, "telegram_chat_id", None))
        self.exchange._notifier = self.notifier
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='market-data')
        self.news_future = None
        self.last_news_poll = 0.0
        self._snapshot = {}
        self.restore()
        self.cash = float(exchange.get_balance('USDT'))
        self._publish()

    def error(self, message: str) -> None:
        self.last_error = message
        self.errors.append({'time': datetime.now(timezone.utc).isoformat(), 'message': message})
        del self.errors[:-20]

    def _record(self, trade: dict) -> None:
        self.tracker.record_trade(trade['symbol'], trade['pnl_pct'], trade['pnl_usd'], trade['reason'])
        self.cooldowns[trade['symbol']] = time.time() + config.symbol_cooldown_minutes * 60
        self.persist()
        try:
            self.journal.log_trade_closed(trade, self.cash)
        except OSError:
            self.error('تعذر تحديث سجل النص؛ بيانات التنفيذ محفوظة في ملف الحالة')
