"""Live crypto news and Binance official announcements fetcher with cryptographic dedup."""
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import time
from typing import List, Any
import requests
from src.config import config
from src.core.models import NewsItem
from src.news.analyzer import NewsAnalyzer
from src.news.binance_announcements import BinanceAnnouncementsScanner
from src.news.dedup_buffer import DedupBuffer

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
        self.last_errors = []

    @staticmethod
    def publication_time(value):
        try:
            if isinstance(value, (int, float)) or str(value).isdigit():
                stamp = float(value)
                return datetime.fromtimestamp(stamp / 1000 if stamp > 1e11 else stamp, timezone.utc)
            date = parsedate_to_datetime(str(value))
            return date.replace(tzinfo=timezone.utc) if date.tzinfo is None else date.astimezone(timezone.utc)
        except (ValueError, TypeError, OverflowError):
            return None

    @staticmethod
    def is_fresh(date):
        return date is not None and -60 <= (datetime.now(timezone.utc) - date).total_seconds() <= config.max_news_age_seconds

    def _fetch_rss(self) -> List[NewsItem]:
        items = []
        for url in FEEDS:
            try:
                r = requests.get(url, timeout=3, headers={"User-Agent": "ScalperBot/1.0"})
                if r.status_code != 200:
                    continue
                root = ET.fromstring(r.content)
                for entry in root.findall(".//item")[:6]:
                    t_elem = entry.find("title")
                    title = t_elem.text.strip() if t_elem is not None and t_elem.text else ""
                    pub = self.publication_time(entry.findtext("pubDate"))
                    if not self.is_fresh(pub) or not title or self.dedup.is_duplicate(title):
                        continue
                    sym = self.analyzer.extract_symbol(title)
                    if sym:
                        score, _ = self.analyzer.analyze_sentiment(title)
                        items.append(NewsItem(title, title, url.split("/")[2], sym, score, pub))
            except Exception as e:
                self.last_errors.append(f"RSS {url.split('/')[2]}: {type(e).__name__}")
        return items

    def fetch_latest_news(self) -> List[NewsItem]:
        items: List[NewsItem] = []
        now = time.time()
        self.last_errors = []
        if now - self._last_cms_time >= 15.0:
            self._last_cms_time = now
            for art in self.binance_scanner.fetch_announcements():
                title, pub = art.get("title", ""), self.publication_time(art.get("releaseDate"))
                if not self.is_fresh(pub) or not title or self.dedup.is_duplicate(title):
                    continue
                sym = self.binance_scanner.extract_listing_ticker(title) or self.analyzer.extract_symbol(title)
                if sym:
                    score, _ = self.analyzer.analyze_sentiment(title)
                    items.append(NewsItem(f"binance_{art.get('id')}", f"[BINANCE OFFICIAL] {title}", "binance.com", sym, score, pub))
        if now - self._last_rss_time >= 45.0:
            self._last_rss_time = now
            items.extend(self._fetch_rss())
        if self.market_scanner:
            for b in self.market_scanner.find_breakouts():
                if not self.dedup.is_duplicate(b.news_id):
                    items.append(b)
        return items
