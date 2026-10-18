"""Live crypto news fetcher from public feeds with deduplication."""
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import List
import requests
from src.core.models import NewsItem
from src.news.analyzer import NewsAnalyzer

logger = logging.getLogger("NewsFetcher")

FEEDS = [
    "https://cryptopanic.com/news/rss/",
    "https://cointelegraph.com/rss",
]


class NewsFetcher:
    def __init__(self, analyzer: NewsAnalyzer):
        self.analyzer = analyzer
        self.seen_ids: set[str] = set()

    def fetch_latest_news(self) -> List[NewsItem]:
        """Fetches and deduplicates latest crypto news items."""
        items: List[NewsItem] = []
        for url in FEEDS:
            try:
                r = requests.get(url, timeout=5, headers={"User-Agent": "ScalperBot/1.0"})
                if r.status_code != 200:
                    continue
                root = ET.fromstring(r.content)
                for entry in root.findall(".//item")[:10]:
                    title_elem = entry.find("title")
                    link_elem = entry.find("link")
                    title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""
                    link = link_elem.text.strip() if link_elem is not None and link_elem.text else title

                    if not title or link in self.seen_ids:
                        continue

                    self.seen_ids.add(link)
                    if len(self.seen_ids) > 1000:
                        self.seen_ids.clear()

                    sym = self.analyzer.extract_symbol(title)
                    if sym:
                        score, _ = self.analyzer.analyze_sentiment(title)
                        items.append(NewsItem(
                            news_id=link,
                            title=title,
                            source=url.split("/")[2],
                            symbol=sym,
                            sentiment_score=score,
                            published_at=datetime.now(timezone.utc),
                        ))
            except Exception as e:
                logger.debug(f"Feed fetch error from {url}: {e}")
        return items
