"""Position execution handler managing full and partial scale-out exits."""
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any
from src.core.models import Position
from src.exchange.base import BaseExchange

logger = logging.getLogger("PositionHandler")


class PositionHandler:
    @staticmethod
    def execute_exit(
        exchange: BaseExchange,
        positions: Dict[str, Position],
        symbol: str,
        reason: str,
        exit_ratio: float,
        trade_history: List[Dict[str, Any]],
    ) -> None:
        """Executes full or partial market sell and records trade PnL."""
        pos = positions.get(symbol)
        if not pos:
            return

        cur_price = exchange.get_ticker_price(symbol)
        sell_qty = pos.amount * exit_ratio

        res = exchange.place_market_sell(symbol, sell_qty)
        if not res.success:
            logger.error(f"Failed to sell {symbol}: {res.message}")
            return

        pnl = (cur_price - pos.entry_price) / pos.entry_price
        trade_history.append({
            "symbol": symbol,
            "pnl_pct": round(pnl * 100, 2),
            "reason": reason,
            "exit_price": cur_price,
            "ratio": exit_ratio,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        if exit_ratio >= 0.99:
            del positions[symbol]
            logger.info(f"Full Exit {symbol}: {reason} | PnL: {pnl*100:.2f}%")
        else:
            pos.amount -= sell_qty
            logger.info(f"Partial Exit 50% {symbol}: {reason} | PnL: {pnl*100:.2f}%")
