"""Universe Manager: Discovers and refreshes top liquid Binance USDT spot pairs."""
import time
import requests
from typing import List, Set
from src.core.ecosystem_registry import EcosystemRegistry


class UniverseManager:
    def __init__(self, min_quote_volume: float = 2000000.0, refresh_interval_sec: float = 600.0):
        self.min_volume = min_quote_volume
        self.refresh_interval = refresh_interval_sec
        self.last_refresh = 0.0
        self.active_universe: List[str] = EcosystemRegistry.get_all_symbols()
        self.session = requests.Session()

    def get_symbols(self) -> List[str]:
        """Returns the current liquid symbols, refreshing periodically from Binance."""
        now = time.time()
        if now - self.last_refresh >= self.refresh_interval or len(self.active_universe) <= 10:
            self.refresh_universe()
        return self.active_universe

    def refresh_universe(self) -> List[str]:
        """Fetches 24hr tickers and filters top liquid USDT spot pairs."""
        try:
            url = "https://api.binance.com/api/v3/ticker/24hr"
            resp = self.session.get(url, timeout=5)
            if resp.status_code == 200:
                tickers = resp.json()
                excluded = {"UPUSDT", "DOWNUSDT", "BEARUSDT", "BULLUSDT", "USDCUSDT", "FDUSDUSDT", "TUSDUSDT", "EURUSDT"}
                candidates = []
                for t in tickers:
                    sym = t.get("symbol", "")
                    if sym.endswith("USDT") and sym not in excluded and not any(sym.endswith(x) for x in ["UPUSDT", "DOWNUSDT"]):
                        vol = float(t.get("quoteVolume", 0.0))
                        if vol >= self.min_volume:
                            candidates.append((sym[:-4] + "/USDT", vol))

                # Sort by volume descending, take top 40 liquid pairs
                candidates.sort(key=lambda x: x[1], reverse=True)
                top_symbols = [c[0] for c in candidates[:40]]

                # Always keep the core anchor ecosystem symbols
                anchors = set(EcosystemRegistry.get_all_symbols())
                unified = list(dict.fromkeys(top_symbols + list(anchors)))
                self.active_universe = unified[:50]
                self.last_refresh = time.time()
        except Exception:
            if not self.active_universe:
                self.active_universe = EcosystemRegistry.get_all_symbols()
        return self.active_universe
