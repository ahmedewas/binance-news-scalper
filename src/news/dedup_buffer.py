"""Cryptographic fingerprint deduplication ring-buffer for sub-millisecond filtering."""
import hashlib
import re
from typing import Set, List


class DedupBuffer:
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._seen_hashes: Set[str] = set()
        self._order_queue: List[str] = []

    @staticmethod
    def _normalize_text(text: str) -> str:
        # Lowercase and remove all non-alphanumeric chars
        return re.sub(r"[^a-z0-9]", "", text.lower())

    def compute_fingerprint(self, text: str) -> str:
        """Computes SHA-256 hash of normalized text."""
        normalized = self._normalize_text(text)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def is_duplicate(self, text: str) -> bool:
        """Returns True if headline was seen before, else registers it and returns False."""
        fp = self.compute_fingerprint(text)
        if fp in self._seen_hashes:
            return True

        self._seen_hashes.add(fp)
        self._order_queue.append(fp)

        # Evict oldest if capacity exceeded
        if len(self._order_queue) > self.max_size:
            oldest = self._order_queue.pop(0)
            self._seen_hashes.discard(oldest)

        return False

    def clear(self) -> None:
        self._seen_hashes.clear()
        self._order_queue.clear()
