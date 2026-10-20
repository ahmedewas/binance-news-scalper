"""Direct Binance Official Announcements API scanner for instant listings."""
import re
import logging
import requests
from typing import List, Dict, Any, Optional

logger = logging.getLogger("BinanceAnnouncements")

BINANCE_CMS_URL = (
    "https://www.binance.com/bapi/composite/v1/public/cms/article/catalog/list/query"
    "?catalogId=48&pageNo=1&pageSize=8"
)


class BinanceAnnouncementsScanner:
    def __init__(self, timeout: int = 4):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        })

    def fetch_announcements(self) -> List[Dict[str, Any]]:
        """Fetches raw latest announcements directly from Binance CMS."""
        try:
            r = self.session.get(BINANCE_CMS_URL, timeout=self.timeout)
            if r.status_code == 200:
                data = r.json()
                payload = data.get("data") or {}
                articles = payload.get("articles", [])
                if not articles:
                    articles = [a for catalog in payload.get("catalogs", [])
                                for a in catalog.get("articles", [])]
                return [
                    {
                        "id": str(a.get("id")),
                        "title": a.get("title", ""),
                        "releaseDate": a.get("releaseDate", 0),
                    }
                    for a in articles
                ]
        except Exception as e:
            logger.debug(f"Binance CMS fetch failed: {e}")
        return []

    def extract_listing_ticker(self, title: str) -> Optional[str]:
        """Extracts target coin ticker from listing announcement."""
        # Examples: "Binance Will List Toncoin (TON)", "Binance Adds SUI..."
        match = re.search(r"\(([A-Z0-9]{2,10})\)", title)
        if match:
            return f"{match.group(1)}/USDT"

        words = title.split()
        for w in words:
            clean = re.sub(r"[^A-Z]", "", w)
            if 2 <= len(clean) <= 6 and clean in ["SOL", "NEAR", "SUI", "APT", "RENDER", "FET", "INJ"]:
                return f"{clean}/USDT"
        return None
