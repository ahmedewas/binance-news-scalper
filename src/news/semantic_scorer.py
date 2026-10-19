"""Semantic Catalyst Classifier with negation and institutional tier ranking."""
import re
from typing import Tuple

NEGATION_PATTERNS = [
    r"\bnot\b", r"\bno\b", r"\bdenies\b", r"\bdenied\b",
    r"\bfake\b", r"\brumor\b", r"\bunconfirmed\b", r"\bfalse\b"
]

TIER1_CATALYSTS = ["will list", "listing", "etf approved", "mainnet launch", "launchpool"]
TIER2_CATALYSTS = ["partnership", "strategic investment", "backed by", "integration"]
TIER3_CATALYSTS = ["upgrade", "burn", "buyback", "expansion", "surge"]
RED_FLAGS = ["hack", "exploit", "sec lawsuit", "delist", "delisting", "insolvent", "freeze"]


class SemanticScorer:
    def classify_catalyst(self, text: str) -> Tuple[float, str]:
        """Classifies news into weighted institutional tiers with negation guard."""
        lowered = text.lower()

        # 1. Critical Red Flag Check
        for rf in RED_FLAGS:
            if re.search(rf, lowered):
                return 0.0, f"CRITICAL_RED_FLAG: {rf}"

        # 2. Negation / Falsification Filter
        has_negation = any(re.search(pat, lowered) for pat in NEGATION_PATTERNS)
        if has_negation:
            return 10.0, "DISCOUNTED: Negation/Rumor detected in context"

        # 3. Tier 1 Catalyst: Binance Listing / Major Milestone
        for c in TIER1_CATALYSTS:
            if c in lowered:
                return 96.0, f"TIER_1_CATALYST: {c.upper()}"

        # 4. Tier 2 Catalyst: Institutional Partnership
        for c in TIER2_CATALYSTS:
            if c in lowered:
                return 84.0, f"TIER_2_CATALYST: {c.upper()}"

        # 5. Tier 3 Catalyst: Protocol Upgrade or Burn
        for c in TIER3_CATALYSTS:
            if c in lowered:
                return 76.0, f"TIER_3_CATALYST: {c.upper()}"

        return 50.0, "NEUTRAL: Standard market headline"
