"""Ecosystem Registry: Classifies assets into 5 Mega Pillars with Sector Leaders."""
from typing import Dict, List, Optional, Tuple, Any

PILLARS: Dict[str, Dict[str, Any]] = {
    "BITCOIN": {
        "leader": "BTC/USDT",
        "name_ar": "منظومة البيتكوين والملاذ الرقمي",
        "followers": ["STX/USDT", "KAS/USDT"],
    },
    "ETHEREUM_L2": {
        "leader": "ETH/USDT",
        "name_ar": "منظومة الإيثيريوم والطبقة الثانية",
        "followers": ["ARB/USDT", "OP/USDT", "POL/USDT", "LINK/USDT", "IMX/USDT", "FTM/USDT"],
    },
    "SOLANA": {
        "leader": "SOL/USDT",
        "name_ar": "منظومة سولانا فائقة السرعة",
        "followers": ["JTO/USDT", "PYTH/USDT", "GALA/USDT"],
    },
    "AI_COMPUTE": {
        "leader": "FET/USDT",
        "name_ar": "منظومة الذكاء الاصطناعي والحوسبة",
        "followers": ["TAO/USDT", "NEAR/USDT", "RENDER/USDT", "INJ/USDT", "GRT/USDT", "FIL/USDT", "ICP/USDT"],
    },
    "NEXTGEN_L1": {
        "leader": "SUI/USDT",
        "name_ar": "منظومة شبكات الجيل الجديد L1",
        "followers": ["APT/USDT", "SEI/USDT", "TIA/USDT", "ALGO/USDT", "VET/USDT", "ADA/USDT", "DOT/USDT", "ATOM/USDT", "AVAX/USDT", "BNB/USDT", "XRP/USDT", "HBAR/USDT"],
    },
}


class EcosystemRegistry:
    @staticmethod
    def get_all_pillars() -> Dict[str, Dict[str, Any]]:
        return PILLARS

    @staticmethod
    def get_pillar_for_symbol(symbol: str) -> Optional[str]:
        for code, data in PILLARS.items():
            if data["leader"] == symbol or symbol in data["followers"]:
                return code
        return None

    @staticmethod
    def get_leader_for_symbol(symbol: str) -> Optional[str]:
        for data in PILLARS.values():
            if data["leader"] == symbol or symbol in data["followers"]:
                return data["leader"]
        return None

    @staticmethod
    def is_leader(symbol: str) -> bool:
        return any(data["leader"] == symbol for data in PILLARS.values())

    @staticmethod
    def get_all_symbols() -> List[str]:
        syms: List[str] = []
        for data in PILLARS.values():
            if data["leader"] not in syms:
                syms.append(data["leader"])
            for fol in data["followers"]:
                if fol not in syms:
                    syms.append(fol)
        return syms
