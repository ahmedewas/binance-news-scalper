"""Application configuration module."""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class AppConfig:
    trading_mode: str = os.getenv("TRADING_MODE", "PAPER").upper()
    api_key: str = os.getenv("BINANCE_API_KEY", "")
    api_secret: str = os.getenv("BINANCE_API_SECRET", "")
    min_notional: float = float(os.getenv("MIN_NOTIONAL", "5.0"))
    max_slots: int = int(os.getenv("MAX_SLOTS", "5"))
    initial_paper_balance: float = float(
        os.getenv("INITIAL_PAPER_BALANCE", "15.0")
    )
    trailing_tp_pct: float = float(os.getenv("TRAILING_TP_PCT", "0.020"))
    trailing_offset_pct: float = float(
        os.getenv("TRAILING_OFFSET_PCT", "0.005")
    )
    stop_loss_pct: float = float(os.getenv("STOP_LOSS_PCT", "0.009"))
    timeout_minutes: int = int(os.getenv("TIMEOUT_MINUTES", "60"))
    min_score: float = float(os.getenv("MIN_PROBABILITY_SCORE", "82.0"))
    port: int = int(os.getenv("PORT", "8080"))
    host: str = os.getenv("HOST", "127.0.0.1")
    dashboard_token: str = os.getenv("DASHBOARD_TOKEN", "")
    state_dir: str = os.getenv("STATE_DIR", "data")
    max_news_age_seconds: int = int(os.getenv("MAX_NEWS_AGE_SECONDS", "900"))
    max_session_loss_pct: float = float(os.getenv("MAX_SESSION_LOSS_PCT", "0.03"))
    enable_flow_entries: bool = os.getenv("ENABLE_FLOW_ENTRIES", "true").lower() == "true"
    enable_volume_decay_exit: bool = os.getenv("ENABLE_VOLUME_DECAY_EXIT", "true").lower() == "true"
    symbol_cooldown_minutes: int = int(os.getenv("SYMBOL_COOLDOWN_MINUTES", "30"))
    max_entries_per_hour: int = int(os.getenv("MAX_ENTRIES_PER_HOUR", "2"))

    def __post_init__(self):
        if self.trading_mode not in {"PAPER", "LIVE"}:
            raise ValueError("TRADING_MODE must be PAPER or LIVE")
        if self.min_notional <= 0 or self.max_slots < 1 or self.initial_paper_balance <= 0:
            raise ValueError("Balance, minimum order and slots must be positive")
        if not 0 < self.stop_loss_pct < 1 or not 0 < self.trailing_offset_pct < 1:
            raise ValueError("Stop and trailing offset must be between 0 and 1")
        if not 0 < self.trailing_tp_pct < 1 or self.timeout_minutes < 1:
            raise ValueError("Invalid take profit or timeout")
        if not 0 <= self.min_score <= 100 or not 0 < self.max_session_loss_pct < 1:
            raise ValueError("Invalid score or session loss limit")
        if self.symbol_cooldown_minutes < 0 or self.max_entries_per_hour < 1 or self.max_news_age_seconds < 1:
            raise ValueError("Invalid cooldown, entry limit or news age")


config = AppConfig()
