"""Live crypto news and Binance official announcements fetcher with cryptographic dedup."""
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import List
import requests
from src.core.models import NewsItem
from src.news.analyzer import NewsAnalyzer
from src.news.dedup_buffer import DedupBuffer
from src.news.binance_announcements import BinanceAnnouncementsScanner

logger = logging.getLogger("NewsFetcher")
FEEDS = ["https://cryptopanic.com/news/rss/", "https://cointelegraph.com/rss"]


class NewsFetcher:
    def __init__(self, analyzer: NewsAnalyzer):
        self.analyzer = analyzer
        self.dedup = DedupBuffer(max_size=1000)
        self.binance_scanner = BinanceAnnouncementsScanner()

    def fetch_latest_news(self) -> List[NewsItem]:
        """Fetches and deduplicates from direct Binance announcements and fast feeds."""
        items: List[NewsItem] = []

        # 1. Direct Binance Official Announcements (Highest Priority)
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

        # 2. General Public RSS Feeds
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

        return items
