"""Fail-closed tests for news freshness, publication dates, and CMS validation."""
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from unittest.mock import MagicMock, patch
import pytest
from src.news.analyzer import NewsAnalyzer
from src.news.fetcher import NewsFetcher


@pytest.mark.parametrize("published", [None, "bad timestamp", 1])
@patch("requests.get")
def test_cms_missing_or_stale_publication_is_rejected(mock_get, published):
    mock_get.return_value.status_code = 404
    fetcher = NewsFetcher(NewsAnalyzer())
    fetcher.binance_scanner = MagicMock()
    fetcher.binance_scanner.fetch_announcements.return_value = [
        {"id": 1, "title": "Binance Will List Arbitrum (ARB)", "releaseDate": published}
    ]
    assert fetcher.fetch_latest_news() == []


@pytest.mark.parametrize("age_days", [None, 10, 0])
@patch("requests.get")
def test_rss_requires_actual_fresh_pubdate(mock_get, age_days):
    date = datetime.now(timezone.utc) - timedelta(days=age_days or 0)
    pubdate = "" if age_days is None else f"<pubDate>{format_datetime(date)}</pubDate>"
    mock_get.return_value.status_code = 200
    mock_get.return_value.content = f"<rss><channel><item><title>Bitcoin upgrade approved</title>{pubdate}</item></channel></rss>".encode()
    fetcher = NewsFetcher(NewsAnalyzer())
    fetcher.binance_scanner = MagicMock()
    fetcher.binance_scanner.fetch_announcements.return_value = []
    items = fetcher.fetch_latest_news()
    if age_days == 0:
        assert len(items) == 1
        assert abs((items[0].published_at - date).total_seconds()) < 1
    else:
        assert items == []
