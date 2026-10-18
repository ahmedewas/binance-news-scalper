"""FastAPI web server exposing mobile REST endpoints and dashboard."""
import os
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from src.engine.bot_worker import BotWorker
from src.config import config


def create_app(worker: BotWorker) -> FastAPI:
    app = FastAPI(title="Binance News Scalper Dashboard")
    static_dir = os.path.join(os.path.dirname(__file__), "static")

    @app.get("/")
    def serve_dashboard():
        return FileResponse(os.path.join(static_dir, "index.html"))

    @app.get("/api/status")
    def get_status():
        usdt = worker.exchange.get_balance("USDT")
        alloc = worker.allocator.calculate_slots(usdt)
        positions_data = [
            {
                "symbol": p.symbol,
                "entry_price": p.entry_price,
                "current_price": worker.exchange.get_ticker_price(p.symbol),
                "highest_price": p.highest_price,
                "pnl_pct": round(
                    ((worker.exchange.get_ticker_price(p.symbol) - p.entry_price) / p.entry_price) * 100, 2
                ),
                "slot_id": p.slot_id,
            }
            for p in worker.positions.values()
        ]
        return JSONResponse({
            "mode": config.trading_mode,
            "is_active": worker.is_active,
            "usdt_balance": usdt,
            "allocation": alloc,
            "open_positions": positions_data,
            "trade_history": worker.trade_history[-10:],
            "latest_news": worker.latest_news[-10:],
        })

    @app.post("/api/toggle")
    def toggle_active():
        worker.is_active = not worker.is_active
        return {"is_active": worker.is_active}

    @app.post("/api/close_all")
    def close_all():
        for sym, pos in list(worker.positions.items()):
            worker.exchange.place_market_sell(sym, pos.amount)
            del worker.positions[sym]
        return {"status": "ALL_POSITIONS_CLOSED"}

    return app
