"""News ticker extraction and semantic catalyst analyzer."""
import re
from typing import Optional, Tuple
from src.news.semantic_scorer import SemanticScorer

POPULAR_TICKERS = {
    "BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "AVAX", "SUI",
    "LINK", "NEAR", "FET", "APT", "DOT", "RENDER", "TAO", "TIA",
    "SEI", "INJ", "ATOM", "OP", "ARB", "ALGO", "POL", "FTM",
    "KAS", "STX", "ICP", "HBAR", "GRT", "FIL", "IMX", "PYTH",
    "JTO", "VET", "GALA"
}


class NewsAnalyzer:
    def __init__(self):
        self.semantic_scorer = SemanticScorer()

    def extract_symbol(self, text: str) -> Optional[str]:
        """Extracts crypto ticker symbol from headline/text."""
        # Preserve case: ordinary words such as 'near' and 'link' are not tickers.
        names = {"bitcoin": "BTC", "ethereum": "ETH", "solana": "SOL", "arbitrum": "ARB"}
        for name, ticker in names.items():
            if re.search(r"\b" + name + r"\b", text, re.I):
                return f"{ticker}/USDT"
        tokens = re.findall(r"\b[A-Z]{2,10}\b", text)
        for token in tokens:
            if token in POPULAR_TICKERS:
                return f"{token}/USDT"
        return None

    def analyze_sentiment(self, text: str) -> Tuple[float, str]:
        """Returns institutional semantic score (0-100) and rationale."""
        return self.semantic_scorer.classify_catalyst(text)
