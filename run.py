"""Main entry point: initializes components, runs background loop and web UI."""
import threading
import time
import logging
from pathlib import Path
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
from src.core.state_store import StateStore
from src.core.audit_journal import AuditJournal
from src.core.process_lock import ProcessLock

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

    # Keep a buffer so the configured stop does not immediately leave dust below
    # the exchange minimum. Per-symbol rules are also checked before each order.
    exit_buffered_minimum = config.min_notional / (1-config.stop_loss_pct) * 1.003
    allocator = PortfolioAllocator(exit_buffered_minimum, config.max_slots)
    regime = MarketRegimeDetector()
    scoring = ScoringEngine(config.min_score)
    risk = RiskManager(
        config.trailing_tp_pct, config.trailing_offset_pct,
        config.stop_loss_pct, config.timeout_minutes
    )
    from src.engine.market_scanner import MarketScanner
    market_scanner = MarketScanner(PaperExchange(0), regime, scoring)
    news_analyzer = NewsAnalyzer()
    news_fetcher = NewsFetcher(news_analyzer, market_scanner)

    data_dir = Path(config.state_dir)
    if not data_dir.is_absolute():
        data_dir = Path(__file__).parent / data_dir
    return BotWorker(exchange, allocator, regime, scoring, risk, news_fetcher,
                     store=StateStore(data_dir / f"state-{config.trading_mode.lower()}.json"),
                     journal=AuditJournal(str(data_dir / f"journal-{config.trading_mode.lower()}.md")))


def worker_loop(worker: BotWorker, stop_event=None):
    stop_event = stop_event or threading.Event()
    logger.info("Starting background trading worker daemon...")
    while not stop_event.is_set():
        try:
            worker.step()
        except Exception as e:
            logger.error(f"Error in worker loop: {e}")
        stop_event.wait(3)


if __name__ == "__main__":
    if (config.host not in {"127.0.0.1", "localhost", "::1"} or config.trading_mode == "LIVE") and len(config.dashboard_token) < 24:
        raise SystemExit("Set a strong DASHBOARD_TOKEN (at least 24 characters) before remote/LIVE access.")
    if config.trading_mode == "LIVE" and not (config.api_key and config.api_secret):
        raise SystemExit("LIVE requires Binance API credentials.")
    state_root = Path(config.state_dir)
    if not state_root.is_absolute():
        state_root = Path(__file__).parent / state_root
    instance_lock = ProcessLock(state_root / f"{config.trading_mode.lower()}.lock")
    server_config = uvicorn.Config("unused", host=config.host, port=config.port, log_level="warning")
    # Reserve the listening port before starting any trading activity.
    server_socket = server_config.bind_socket()
    worker = build_worker()
    stop = threading.Event()
    t = threading.Thread(target=worker_loop, args=(worker, stop), daemon=True)
    t.start()

    app = create_app(worker)
    server_config.app = app
    logger.info(f"Serving Dashboard on http://{config.host}:{config.port}")
    try:
        uvicorn.Server(server_config).run(sockets=[server_socket])
    finally:
        stop.set()
        t.join(timeout=20)
        worker.shutdown()
        server_socket.close()
        instance_lock.close()
