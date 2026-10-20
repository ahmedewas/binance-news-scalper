"""Unit tests for NewsFetcher throttling and dedup integration."""
import time
from unittest.mock import MagicMock, patch
from src.news.fetcher import NewsFetcher
from src.news.analyzer import NewsAnalyzer


def test_news_fetcher_initialization():
    analyzer = NewsAnalyzer()
    fetcher = NewsFetcher(analyzer=analyzer)
    assert fetcher.dedup is not None
    assert fetcher._last_cms_time == 0.0
    assert fetcher._last_rss_time == 0.0


@patch("requests.get")
def test_news_fetcher_with_mocked_sources(mock_get):
    mock_get.return_value.status_code = 404
    analyzer = NewsAnalyzer()
    mock_scanner = MagicMock()
    mock_scanner.fetch_announcements.return_value = [
        {"id": 123, "releaseDate": int(time.time() * 1000), "title": "Binance Will List Arbitrum (ARB) with Seed Tag"}
    ]
    mock_scanner.extract_listing_ticker.return_value = "ARB/USDT"
    mock_market = MagicMock()
    mock_market.find_breakouts.return_value = []

    fetcher = NewsFetcher(analyzer=analyzer, market_scanner=mock_market)
    fetcher.binance_scanner = mock_scanner

    items = fetcher.fetch_latest_news()
    assert len(items) >= 1
    assert any("ARB/USDT" in item.symbol for item in items)


@patch("requests.get")
def test_news_fetcher_throttling(mock_get):
    mock_get.return_value.status_code = 404
    analyzer = NewsAnalyzer()
    mock_scanner = MagicMock()
    mock_scanner.fetch_announcements.return_value = []
    fetcher = NewsFetcher(analyzer=analyzer)
    fetcher.binance_scanner = mock_scanner

    # First call triggers fetch
    fetcher.fetch_latest_news()
    assert mock_scanner.fetch_announcements.call_count == 1

    # Immediate second call should be throttled (15s throttle)
    fetcher.fetch_latest_news()
    assert mock_scanner.fetch_announcements.call_count == 1
