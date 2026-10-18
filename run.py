"""Main entry point: initializes components, runs background loop and web UI."""
import threading
import time
import logging
import uvicorn
from src.config import config
from src.core.portfolio_allocator import PortfolioAllocator
from src.core.regime_detector import MarketRegimeDetector
from src.core.scoring_engine import ScoringEngine
from src.core.risk_manager import RiskManager
from src.news.analyzer import NewsAnalyzer
from src.news.fetcher import NewsFetcher
from src.exchange.paper import PaperExchange
from src.exchange.live import LiveExchange
from src.engine.bot_worker import BotWorker
from src.web.app import create_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("Main")


def build_worker() -> BotWorker:
    if config.trading_mode == "LIVE":
        logger.info("Initializing LIVE Binance Spot Exchange via CCXT...")
        exchange = LiveExchange(config.api_key, config.api_secret)
    else:
        logger.info(f"Initializing PAPER Exchange with ${config.initial_paper_balance}...")
        exchange = PaperExchange(config.initial_paper_balance)

    allocator = PortfolioAllocator(config.min_notional, config.max_slots)
    regime = MarketRegimeDetector()
    scoring = ScoringEngine(config.min_score)
    risk = RiskManager(
        config.trailing_tp_pct, config.trailing_offset_pct,
        config.stop_loss_pct, config.timeout_minutes
    )
    news_analyzer = NewsAnalyzer()
    news_fetcher = NewsFetcher(news_analyzer)

    return BotWorker(exchange, allocator, regime, scoring, risk, news_fetcher)


def worker_loop(worker: BotWorker):
    logger.info("Starting background trading worker daemon...")
    while True:
        try:
            worker.step()
        except Exception as e:
            logger.error(f"Error in worker loop: {e}")
        time.sleep(3)


if __name__ == "__main__":
    worker = build_worker()
    t = threading.Thread(target=worker_loop, args=(worker,), daemon=True)
    t.start()

    app = create_app(worker)
    logger.info(f"Serving Mobile Web Dashboard on http://0.0.0.0:{config.port}")
    uvicorn.run(app, host="0.0.0.0", port=config.port, log_level="warning")
