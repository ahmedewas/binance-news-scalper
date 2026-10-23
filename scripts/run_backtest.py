"""CLI runner for historical backtesting across liquid Binance Halal coins."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.exchange.paper import PaperExchange
from src.core.backtest_engine import FastBacktester


def run_quick_audit():
    print("==================================================")
    print("SIMPLIFIED RESEARCH MODEL - NOT LIVE STRATEGY VALIDATION")
    print("Independent capital per symbol; aggregate is not a shared portfolio. No slippage model.")
    print("==================================================")
    exchange = PaperExchange()
    tester = FastBacktester()
    symbols = ["SOL/USDT", "NEAR/USDT", "ALGO/USDT", "STX/USDT", "FET/USDT"]

    all_trades = []
    print("\nFetching recent market data and simulating...")
    for sym in symbols:
        klines = exchange.get_historical_klines(sym, "1m", 120)
        if not klines:
            continue
        trades = tester.simulate_symbol(sym, klines, min_score=72.0, sl_pct=0.009, tp_pct=0.012)
        all_trades.extend(trades)
        print(f"  {sym}: {len(klines)} candles -> {len(trades)} trades simulated")

    perf = tester.evaluate_performance(all_trades)
    print("\n--- BACKTEST SUMMARY RESULTS ---")
    print(f"Total Simulated Trades: {perf['total_trades']}")
    print(f"Win Rate:               {perf['win_rate']}% ({perf['wins']} wins / {perf['losses']} losses)")
    print(f"Net PnL USD:            ${perf['net_pnl_usd']:+.4f}")
    print(f"Profit Factor:          {perf['profit_factor']}")
    print("==================================================")


if __name__ == "__main__":
    run_quick_audit()
