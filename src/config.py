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
    trailing_tp_pct: float = float(os.getenv("TRAILING_TP_PCT", "0.012"))
    trailing_offset_pct: float = float(
        os.getenv("TRAILING_OFFSET_PCT", "0.004")
    )
    stop_loss_pct: float = float(os.getenv("STOP_LOSS_PCT", "0.009"))
    timeout_minutes: int = int(os.getenv("TIMEOUT_MINUTES", "20"))
    min_score: float = float(os.getenv("MIN_PROBABILITY_SCORE", "75.0"))
    port: int = int(os.getenv("PORT", "8080"))


config = AppConfig()
