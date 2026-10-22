# Living Memory & Project State Tracking: Binance News Scalper

## 1. Locked Working Modules (قائمة الخطوط الحمراء)
- [x] **Bitcoin Flash Crash Gate (`src/core/btc_gate.py`):** Real-time BTC monitoring vetoing all altcoin entries if BTC drops >0.4% or experiences aggressive sell-volume spikes.
- [x] **Multi-Timeframe 15m Confluence (`src/core/mtf_confluence.py`):** Higher-timeframe trend alignment (EMA9 vs EMA21 and structural lower-lows), eliminating counter-trend trap trades.
- [x] **Weighted Institutional Scoring Engine (`src/core/scoring_engine.py`):** 40% Volume/CVD + 30% Regime + 30% Momentum/Catalyst, calibrated with dynamic regulator and fractal Hurst filter.
- [x] **Market-Adaptive Score Regulator (`src/core/adaptive_regulator.py`):** Dynamic threshold scaling between 70.0 (bullish) and 85.0 (bearish/sideways defense), plus emergency lockout (99.0).
- [x] **Ratcheted Ladder Profit Lock (`src/core/risk_manager.py`):** 4-tier ratcheting stop (+0.6% locks +0.2% fee coverage, +1.2% locks +0.8%, +2.0% locks +1.5%, +3.0% locks +2.4%) with ATR targets support.
- [x] **Order Book Imbalance (OBI) Guard (`src/exchange/orderbook_depth.py`):** Real-time L2 top-20 bid/ask depth analyzer rejecting buys against heavy ask walls ($OBI < -0.30$) with fail-safe guard.
- [x] **Optimized Volume Decay Breathing Room (`src/core/volume_decay_exit.py`):** Extended evaluation threshold to 14 minutes, eliminating premature fee-bleeding exits.
- [x] **Dynamic ATR Volatility Targets (`src/core/atr_calculator.py`):** Adaptive TP (+0.8% to +3.0%) and SL (-0.6% to -1.5%) scaled to each coin's unique intraday volatility and wired to Position.
- [x] **Symbol Cooldown Buffer (`src/core/cooldown_manager.py`):** 15-minute mandatory buffer on exited symbols preventing churn loops, preserved across mode switches.
- [x] **Expanded 35 Halal Spot Universe (`src/engine/market_scanner.py` & `src/news/analyzer.py`):** Tier-1 liquid non-lending Halal coins including KAS, STX, ICP, HBAR, GRT, FIL, IMX, PYTH, JTO, VET, GALA.
- [x] **High-Speed Hybrid Stream Manager (`src/news/stream_manager.py`):** Dual-mode WebSocket with high-speed connection-pooled REST fallback for sub-second updates across all regions.
- [x] **Cross-Asset Sector Lead-Lag Latency Arbitrage (`src/core/lead_lag_correlator.py`):** Cluster pairs (SOL->JTO/PYTH, FET->RENDER/TAO, BTC->STX/KAS, ETH->ARB/OP/IMX).
- [x] **Anti-Slippage Execution Shield (`src/exchange/slippage_guard.py`):** Validates market buy spreads (<=0.25%) and sell bid depth (<=0.35%) before routing.
- [x] **Exact Binance Order Precision Sanitizer (`src/exchange/precision_formatter.py`):** Exact Decimal quantization respecting arbitrary exchange LOT_SIZE step sizes (0.05, 0.2, 0.5, 2.0).
- [x] **Interactive 2-Way Telegram Bot (`src/core/telegram_command_listener.py`):** Background thread polling `getUpdates` with defensive exception handling for `/status`, `/close_all`, `/pause`, `/resume`, `/autopsy`.
- [x] **Asynchronous Telegram Alert Daemon (`src/core/telegram_notifier.py`):** Background thread dispatching mobile buy/sell/PnL notifications, preserved across runtime mode switches.
- [x] **Automated Session Diagnostic Autopsy (`src/core/session_autopsy.py`):** Forensic performance analyzer with `/api/autopsy` diagnostic route.
- [x] **Intrabar Real-Time Backtester & Optimizer (`src/core/backtest_engine.py` & `scripts/run_backtest.py`):** Intrabar high/low simulation on 1m klines eliminating look-ahead bias.
- [x] **Dashboard Mode Switching Controller (`src/engine/worker_admin.py`, `src/web/app.py`, `src/web/static/`):** Instant runtime toggle between Paper Simulation and Live Trading with state store synchronization.
- [x] **Opportunity Filters Decomposition (`src/engine/opportunity_filters.py`):** Modular quantitative macro gate, Hurst/CVD alpha computation, and microstructure checks.
- [x] **Modular Engine Architecture (`src/engine/`):** Full decoupling into `bot_worker.py`, `worker_snapshot.py`, `worker_order_ops.py`, `worker_cycle.py`, `worker_admin.py`, `worker_state.py`.
- [x] **Modular Exchange Architecture (`src/exchange/`):** CCXT execution separated into `live.py`, `live_orders.py`, and self-healing `paper.py`.
- [x] **Protocol 7 Modularity Compliance:** 100% of files in `src/` and `tests/` strictly <= 100 lines.
- [x] **Automated Test Suite:** 161/161 unit and regression tests passing with 100% success rate in 2.59s.

## 2. Cumulative Requirements Registry (سجل المتطلبات التراكمية)
1. **Spot Only:** No leverage, zero liquidation risk, 100% Halal compliant.
2. **Capital Velocity:** Multi-stage 50% partial exit, 14-min volume decay recycling, and 20-min max trade lifespan.
3. **Institutional Alpha Edge:**
   - Multi-stage 50% scale-out with free-ride trailing stop.
   - Preemptive volume decay exit after 14-min breathing room.
   - Sub-second direct Binance CMS listing announcements scanner.
   - Contextual semantic catalyst classification (Tier 1-3) with negation defense.
   - SHA-256 cryptographic headline deduplication.
   - SMC Fair Value Gap (FVG) liquidity void expansion.
   - Wyckoff Volume Absorption (Springs) and Distribution Upthrusts (UTAD).
   - Fractional Kelly Criterion sizing based on empirical edge.
   - Hurst Exponent chaos rejection ($H > 0.52$) active in live scoring.
   - Market maker inventory depletion frontrunning.
   - Lead-Lag cross-asset latency arbitrage across 35 Halal coins.
   - Cumulative Volume Delta (CVD) order flow active in live scoring.
   - Bitcoin flash-crash veto gate ($< -0.4\%$).
   - Multi-timeframe (15m) trend alignment filter.
   - Dynamic Market-Adaptive score regulator (70.0 - 85.0 scaling based on BTC macro climate).
   - Ratcheted ladder profit lock with 4 locked profit tiers and dynamic ATR targets.
   - Order Book Imbalance (OBI) guard with fail-safe wall rejection.
   - Interactive 2-Way Telegram Bot commands with exception safety.
   - Intrabar offline backtester and parameter optimizer.
   - Anti-slippage shield preventing adverse fills.
   - Exact Decimal lot-size and tick precision sanitization.
   - Asynchronous Telegram mobile notifications with runtime preservation.
   - Automated session diagnostic autopsy.
4. **Dynamic Sizing ($5 Min Notional):** Respects Binance limits, auto-calculates concurrent slots.
5. **Dual Mode:** Paper trading default, toggleable to Live with synchronized state store and persistence.
6. **Mobile Independence:** Continues executing in cloud/server even when phone is powered off.

## 3. Active Sprint Status
- **Current Milestone:** Swarm Intelligence Audit & Comprehensive Code Fortification COMPLETE.
- **Precision LOT_SIZE Math:** FIXED (Exact Decimal Quantization for non-decimal steps).
- **Mode Switching Re-Wiring:** FIXED (`_cooldown_mgr`, `_notifier`, and state path synchronized).
- **Alpha Pipeline Integration:** FIXED (`HurstFilter` and `CVDTracker` wired into scoring).
- **Dynamic ATR Targets:** FIXED (Wired into `Position` and executed in `RiskManager`).
- **Disk I/O Thrashing:** ELIMINATED (Removed unconditional 3s fsync persistence).
- **Thread Concurrency:** SECURED (Locked `cash` balance and candidate list mutations).
- **Backtester Intrabar Bias:** FIXED (Simulates intrabar high/low execution limits).
- **Telegram `/resume` Safety:** FIXED (Graceful error handling and Arabic user replies).
- **Test Verification:** 161/161 automated tests passing with zero errors (100% pass rate).
- **Protocol 7 Compliance:** ZERO files exceeding 100 lines across `src/` and `tests/`.
