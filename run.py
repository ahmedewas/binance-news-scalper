"""Main entry point: initializes components, runs background loop and web UI."""
import threading
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("Main")


def build_worker() -> BotWorker:
    exchange = LiveExchange(config.api_key, config.api_secret) if config.trading_mode == "LIVE" else PaperExchange(config.initial_paper_balance)
    exit_min = config.min_notional / (1 - config.stop_loss_pct) * 1.003
    allocator = PortfolioAllocator(exit_min, config.max_slots)
    regime = MarketRegimeDetector()
    scoring = ScoringEngine(config.min_score)
    risk = RiskManager(config.trailing_tp_pct, config.trailing_offset_pct, config.stop_loss_pct, config.timeout_minutes)
    from src.engine.market_scanner import MarketScanner
    fetcher = NewsFetcher(NewsAnalyzer(), MarketScanner(PaperExchange(0), regime, scoring))
    data_dir = Path(config.state_dir)
    data_dir = data_dir if data_dir.is_absolute() else Path(__file__).parent / data_dir
    return BotWorker(exchange, allocator, regime, scoring, risk, fetcher,
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
    state_root = state_root if state_root.is_absolute() else Path(__file__).parent / state_root
    instance_lock = ProcessLock(state_root / f"{config.trading_mode.lower()}.lock")
    server_config = uvicorn.Config("unused", host=config.host, port=config.port, log_level="warning")
    server_socket = server_config.bind_socket()
    worker = build_worker()
    if getattr(config, "telegram_bot_token", None) and getattr(config, "telegram_chat_id", None):
        from src.core.telegram_command_listener import TelegramCommandListener
        TelegramCommandListener(config.telegram_bot_token, config.telegram_chat_id, worker).start()
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
