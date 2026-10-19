"""FastAPI web server exposing mobile REST endpoints and dashboard."""
import os
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from src.engine.bot_worker import BotWorker
from src.config import config
from src.core.performance_tracker import PerformanceTracker
from src.engine.market_scanner import MarketScanner
from src.engine.position_handler import PositionHandler


def create_app(worker: BotWorker) -> FastAPI:
    app = FastAPI(title="Binance News Scalper Dashboard")
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    tracker = getattr(worker, "tracker", PerformanceTracker(config.initial_paper_balance))
    scanner = getattr(worker.news_fetcher, "market_scanner", None) or MarketScanner(
        worker.exchange, worker.regime_detector, worker.scoring_engine
    )

    @app.get("/")
    def serve_dashboard():
        return FileResponse(os.path.join(static_dir, "index.html"))

    @app.get("/api/status")
    def get_status():
        usdt = worker.exchange.get_balance("USDT")
        eq = usdt + sum(p.amount * p.current_price for p in worker.positions.values())
        alloc = worker.allocator.calculate_slots(usdt, eq)
        now = datetime.now(timezone.utc)
        positions_data = []
        for p in worker.positions.values():
            cur_p = worker.exchange.get_ticker_price(p.symbol)
            pnl_pct = round(((cur_p - p.entry_price) / p.entry_price) * 100, 2)
            pnl_usd = round((cur_p - p.entry_price) * p.amount, 4)
            elapsed = round((now - p.entry_time).total_seconds() / 60, 1)
            positions_data.append({
                "symbol": p.symbol, "entry_price": p.entry_price, "current_price": cur_p,
                "cost_basis": round(p.entry_price * p.amount, 2), "pnl_usd": pnl_usd,
                "pnl_pct": pnl_pct, "highest_price": p.highest_price,
                "target_tp": round(p.entry_price * (1 + config.trailing_tp_pct), 4),
                "stop_loss": round(p.entry_price * (1 - config.stop_loss_pct), 4),
                "is_breakeven_locked": p.is_breakeven_locked, "partial_tp_done": p.partial_tp_done,
                "elapsed_mins": elapsed, "remaining_mins": max(0.0, round(config.timeout_minutes - elapsed, 1)),
                "slot_id": p.slot_id,
            })

        return JSONResponse({
            "mode": config.trading_mode, "is_active": worker.is_active,
            "usdt_balance": usdt, "allocation": alloc, "open_positions": positions_data,
            "trade_history": worker.trade_history[-15:], "latest_news": worker.latest_news[-10:],
            "performance": tracker.get_summary(eq),
            "market_radar": scanner.cached_results,
        })

    @app.post("/api/toggle")
    def toggle_active():
        worker.is_active = not worker.is_active
        return {"is_active": worker.is_active}

    @app.post("/api/close_all")
    def close_all():
        for sym in list(worker.positions.keys()):
            PositionHandler.execute_exit(
                worker.exchange, worker.positions, sym, "MANUAL_CLOSE", 1.0, worker.trade_history
            )
            if worker.trade_history:
                l = worker.trade_history[-1]
                worker.tracker.record_trade(l["symbol"], l["pnl_pct"], l["pnl_usd"], l["reason"])
                worker.journal.log_trade_closed(l, worker.exchange.get_balance("USDT"))
        return {"status": "ALL_POSITIONS_CLOSED"}

    @app.get("/api/journal")
    def get_journal():
        return {"journal": worker.journal.read_journal()}

    return app
