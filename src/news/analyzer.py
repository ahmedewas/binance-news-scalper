"""News ticker extraction and semantic catalyst analyzer."""
import re
from typing import Optional, Tuple
from src.news.semantic_scorer import SemanticScorer

POPULAR_TICKERS = {
    "BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "AVAX", "DOGE",
    "NEAR", "SUI", "APT", "INJ", "LINK", "ARB", "OP", "TIA",
    "SEI", "RENDER", "FET", "PEPE", "SHIB", "DOT", "MATIC"
}


class NewsAnalyzer:
    def __init__(self):
        self.semantic_scorer = SemanticScorer()

    def extract_symbol(self, text: str) -> Optional[str]:
        """Extracts crypto ticker symbol from headline/text."""
        tokens = re.findall(r"\b[A-Z]{2,10}\b", text.upper())
        for token in tokens:
            if token in POPULAR_TICKERS:
                return f"{token}/USDT"
        return None

    def analyze_sentiment(self, text: str) -> Tuple[float, str]:
        """Returns institutional semantic score (0-100) and rationale."""
        return self.semantic_scorer.classify_catalyst(text)
