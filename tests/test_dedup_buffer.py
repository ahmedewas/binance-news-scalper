"""Unit tests for Cryptographic Fingerprint DedupBuffer."""
from src.news.dedup_buffer import DedupBuffer


def test_dedup_exact_match():
    buffer = DedupBuffer(max_size=10)
    assert not buffer.is_duplicate("Bitcoin reaches all time high")
    assert buffer.is_duplicate("Bitcoin reaches all time high")


def test_dedup_normalized_case_and_punctuation():
    buffer = DedupBuffer(max_size=10)
    assert not buffer.is_duplicate("Solana Breaks Out!!!")
    # Case insensitive, punctuation removed -> treated as duplicate
    assert buffer.is_duplicate("solana breaks out")


def test_dedup_eviction():
    buffer = DedupBuffer(max_size=2)
    buffer.is_duplicate("Item 1")
    buffer.is_duplicate("Item 2")
    # Evicts Item 1 when Item 3 is added
    buffer.is_duplicate("Item 3")
    assert not buffer.is_duplicate("Item 1")
