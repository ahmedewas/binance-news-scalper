"""News ticker extraction and sentiment scoring analyzer."""
import re
from typing import Optional, Tuple

POSITIVE_KEYWORDS = [
    "listing", "partnership", "mainnet", "upgrade", "launch",
    "approved", "surge", "breakout", "investment", "integration",
    "burn", "rally", "record", "backing", "expansion"
]

NEGATIVE_KEYWORDS = [
    "hack", "exploit", "lawsuit", "sec", "ban", "delist",
    "freeze", "halt", "dump", "scam", "bankruptcy", "breach"
]

POPULAR_TICKERS = {
    "BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "AVAX", "DOGE",
    "NEAR", "SUI", "APT", "INJ", "LINK", "ARB", "OP", "TIA",
    "SEI", "RENDER", "FET", "PEPE", "SHIB", "DOT", "MATIC"
}


class NewsAnalyzer:
    def extract_symbol(self, text: str) -> Optional[str]:
        """Extracts crypto ticker symbol from headline/text."""
        tokens = re.findall(r"\b[A-Z]{2,10}\b", text.upper())
        for token in tokens:
            if token in POPULAR_TICKERS:
                return f"{token}/USDT"
        return None

    def analyze_sentiment(self, text: str) -> Tuple[float, str]:
        """Returns sentiment score (0-100) and rationale."""
        lowered = text.lower()
        pos_hits = sum(1 for kw in POSITIVE_KEYWORDS if kw in lowered)
        neg_hits = sum(1 for kw in NEGATIVE_KEYWORDS if kw in lowered)

        if neg_hits > 0 and neg_hits >= pos_hits:
            score = max(0.0, 30.0 - neg_hits * 15.0)
            return score, f"Negative keywords: {neg_hits}"

        if pos_hits > 0:
            score = min(100.0, 65.0 + pos_hits * 12.0)
            return score, f"Positive catalysts: {pos_hits}"

        return 50.0, "Neutral headline"
