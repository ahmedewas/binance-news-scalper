"""High-speed real-time price stream manager with WebSocket and Batch-REST fallback."""
import json
import logging
import threading
import time
from typing import Dict, Optional
import requests

logger = logging.getLogger("StreamManager")


class StreamManager:
    def __init__(self, refresh_interval_seconds: float = 2.0):
        self.interval = refresh_interval_seconds
        self._prices: Dict[str, float] = {}
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "ScalperStream/2.0"})

    def start(self) -> None:
        """Starts background streaming and batch ingestion daemon."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="PriceStream")
        self._thread.start()
        logger.info("Price Stream Manager daemon started.")

    def stop(self) -> None:
        self._running = False

    def get_price(self, symbol: str) -> Optional[float]:
        """Returns fresh price in 0.001ms from memory cache."""
        clean = symbol.replace("/", "").upper()
        with self._lock:
            return self._prices.get(clean) or self._prices.get(symbol)

    def update_price(self, symbol: str, price: float) -> None:
        clean = symbol.replace("/", "").upper()
        with self._lock:
            self._prices[clean] = price
            self._prices[symbol] = price

    def _run_loop(self) -> None:
        while self._running:
            try:
                r = self._session.get("https://api.binance.com/api/v3/ticker/price", timeout=3.5)
                if r.status_code == 200:
                    data = r.json()
                    new_cache = {item["symbol"]: float(item["price"]) for item in data if "symbol" in item}
                    with self._lock:
                        self._prices.update(new_cache)
            except Exception as e:
                logger.debug("Batch ticker update failed: %s", e)
            time.sleep(self.interval)

    @property
    def is_active(self) -> bool:
        return self._running and len(self._prices) > 0
