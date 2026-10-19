"""Domain models and data structures."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class MarketPhase(str, Enum):
    ACCUMULATION = "ACCUMULATION"
    MARKUP = "MARKUP"
    DISTRIBUTION = "DISTRIBUTION"
    MARKDOWN = "MARKDOWN"


@dataclass
class NewsItem:
    news_id: str
    title: str
    source: str
    symbol: str
    sentiment_score: float
    published_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ScoringResult:
    symbol: str
    phase: MarketPhase
    phase_score: float
    momentum_score: float
    volume_score: float
    news_score: float
    total_score: float
    is_approved: bool
    rejection_reason: Optional[str] = None


@dataclass
class Position:
    symbol: str
    entry_price: float
    current_price: float
    amount: float
    highest_price: float
    entry_time: datetime
    slot_id: int
    is_breakeven_locked: bool = False


@dataclass
class OrderResult:
    success: bool
    order_id: str
    symbol: str
    price: float
    amount: float
    side: str
    status: str
    message: str = ""
