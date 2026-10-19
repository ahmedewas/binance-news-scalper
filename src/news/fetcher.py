"""Live crypto news and Binance official announcements fetcher with cryptographic dedup."""
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import List, Any
import time
import requests
from src.core.models import NewsItem
from src.news.analyzer import NewsAnalyzer
from src.news.dedup_buffer import DedupBuffer
from src.news.binance_announcements import BinanceAnnouncementsScanner

logger = logging.getLogger("NewsFetcher")
FEEDS = ["https://cryptopanic.com/news/rss/", "https://cointelegraph.com/rss"]


class NewsFetcher:
    def __init__(self, analyzer: NewsAnalyzer, market_scanner: Any = None):
        self.analyzer = analyzer
        self.market_scanner = market_scanner
        self.dedup = DedupBuffer(max_size=1000)
        self.binance_scanner = BinanceAnnouncementsScanner()
        self._last_cms_time: float = 0.0
        self._last_rss_time: float = 0.0

    def fetch_latest_news(self) -> List[NewsItem]:
        """Fetches from Binance listings, RSS feeds, and 24-coin Spot breakouts."""
        items: List[NewsItem] = []
        now = time.time()

        # 1. Direct Binance Official Announcements (15s throttle)
        if now - self._last_cms_time >= 15.0:
            self._last_cms_time = now
            for article in self.binance_scanner.fetch_announcements():
                title = article.get("title", "")
                if not title or self.dedup.is_duplicate(title):
                    continue
                sym = self.binance_scanner.extract_listing_ticker(title) or self.analyzer.extract_symbol(title)
                if sym:
                    score, _ = self.analyzer.analyze_sentiment(title)
                    items.append(NewsItem(
                        news_id=f"binance_{article.get('id')}",
                        title=f"[BINANCE OFFICIAL] {title}",
                        source="binance.com",
                        symbol=sym,
                        sentiment_score=score,
                        published_at=datetime.now(timezone.utc),
                    ))

        # 2. General Public RSS Feeds (45s throttle)
        if now - self._last_rss_time >= 45.0:
            self._last_rss_time = now
            for url in FEEDS:
                try:
                    r = requests.get(url, timeout=3, headers={"User-Agent": "ScalperBot/1.0"})
                    if r.status_code != 200:
                        continue
                    root = ET.fromstring(r.content)
                    for entry in root.findall(".//item")[:6]:
                        t_elem = entry.find("title")
                        title = t_elem.text.strip() if t_elem is not None and t_elem.text else ""
                        if not title or self.dedup.is_duplicate(title):
                            continue
                        sym = self.analyzer.extract_symbol(title)
                        if sym:
                            score, _ = self.analyzer.analyze_sentiment(title)
                            items.append(NewsItem(
                                news_id=title,
                                title=title,
                                source=url.split("/")[2],
                                symbol=sym,
                                sentiment_score=score,
                                published_at=datetime.now(timezone.utc),
                            ))
                except Exception as e:
                    logger.debug(f"Feed fetch error from {url}: {e}")

        # 3. Live Binance Spot Breakouts on 24 Halal Coins
        if self.market_scanner:
            for b in self.market_scanner.find_breakouts():
                if not self.dedup.is_duplicate(b.news_id):
                    items.append(b)

        return items
