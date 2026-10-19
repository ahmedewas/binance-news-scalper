"""Unit tests for Binance Announcements Scanner."""
from src.news.binance_announcements import BinanceAnnouncementsScanner


def test_extract_ticker_with_parentheses():
    scanner = BinanceAnnouncementsScanner()
    ticker = scanner.extract_listing_ticker("Binance Will List Toncoin (TON) with Seed Tag Applied")
    assert ticker == "TON/USDT"


def test_extract_ticker_without_parentheses():
    scanner = BinanceAnnouncementsScanner()
    ticker = scanner.extract_listing_ticker("Binance Adds SUI to Simple Earn and Margin")
    assert ticker == "SUI/USDT"


def test_extract_ticker_unrelated():
    scanner = BinanceAnnouncementsScanner()
    ticker = scanner.extract_listing_ticker("Binance Completes Scheduled Wallet Maintenance")
    assert ticker is None
