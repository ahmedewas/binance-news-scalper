# Living Memory & Project State Tracking: Binance News Scalper

## 1. Locked Working Modules (قائمة الخطوط الحمراء)
- [x] **Bitcoin Flash Crash Gate (`src/core/btc_gate.py`):** Real-time BTC monitoring vetoing all altcoin entries if BTC drops >0.4% or experiences aggressive sell-volume spikes.
- [x] **Multi-Timeframe 15m Confluence (`src/core/mtf_confluence.py`):** Higher-timeframe trend alignment (EMA9 vs EMA21 and structural lower-lows), eliminating counter-trend trap trades.
- [x] **Weighted Institutional Scoring Engine (`src/core/scoring_engine.py`):** 40% Volume/CVD + 30% Regime + 30% Momentum/Catalyst, calibrated with dynamic regulator.
- [x] **Market-Adaptive Score Regulator (`src/core/adaptive_regulator.py`):** Dynamic threshold scaling between 70.0 (bullish) and 85.0 (bearish/sideways defense), plus emergency lockout (99.0).
- [x] **Ratcheted Ladder Profit Lock (`src/core/risk_manager.py`):** 4-tier ratcheting stop (+0.6% locks +0.2% fee coverage, +1.2% locks +0.8%, +2.0% locks +1.5%, +3.0% locks +2.4%).
- [x] **Order Book Imbalance (OBI) Guard (`src/exchange/orderbook_depth.py`):** Real-time L2 top-20 bid/ask depth analyzer rejecting buys against heavy ask walls ($OBI < -0.30$).
- [x] **Optimized Volume Decay Breathing Room (`src/core/volume_decay_exit.py`):** Extended evaluation threshold to 14 minutes, eliminating premature fee-bleeding exits.
- [x] **Dynamic ATR Volatility Targets (`src/core/atr_calculator.py`):** Adaptive TP (+0.8% to +3.0%) and SL (-0.6% to -1.5%) scaled to each coin's unique intraday volatility.
- [x] **Symbol Cooldown Buffer (`src/core/cooldown_manager.py`):** 15-minute mandatory buffer on exited symbols preventing churn loops.
- [x] **Expanded 35 Halal Spot Universe (`src/engine/market_scanner.py` & `src/news/analyzer.py`):** Tier-1 liquid non-lending Halal coins including KAS, STX, ICP, HBAR, GRT, FIL, IMX, PYTH, JTO, VET, GALA.
- [x] **High-Speed Hybrid Stream Manager (`src/news/stream_manager.py`):** Dual-mode WebSocket with high-speed connection-pooled REST fallback for sub-second updates across all regions.
- [x] **Cross-Asset Sector Lead-Lag Latency Arbitrage (`src/core/lead_lag_correlator.py`):** Cluster pairs (SOL->JTO/PYTH, FET->RENDER/TAO, BTC->STX/KAS, ETH->ARB/OP/IMX).
- [x] **Anti-Slippage Execution Shield (`src/exchange/slippage_guard.py`):** Validates market buy spreads (<=0.25%) and sell bid depth (<=0.35%) before routing.
- [x] **Binance Order Precision Sanitizer (`src/exchange/precision_formatter.py`):** Enforces exchange LOT_SIZE step sizes and min notional ($5 USDT) limits.
- [x] **Interactive 2-Way Telegram Bot (`src/core/telegram_command_listener.py`):** Background thread polling `getUpdates` for `/status`, `/close_all`, `/pause`, `/resume`, `/autopsy`.
- [x] **Asynchronous Telegram Alert Daemon (`src/core/telegram_notifier.py`):** Background thread dispatching mobile buy/sell/PnL notifications.
- [x] **Automated Session Diagnostic Autopsy (`src/core/session_autopsy.py`):** Forensic performance analyzer with `/api/autopsy` diagnostic route.
- [x] **Fast Offline Backtester & Strategy Optimizer (`src/core/backtest_engine.py` & `scripts/run_backtest.py`):** Historical 1m kline simulation with breakout signals and ratcheted ladder exits.
- [x] **Dashboard Mode Switching Controller (`src/engine/worker_admin.py`, `src/web/app.py`, `src/web/static/`):** Instant runtime toggle between Paper Simulation and Live Trading via Web UI and API.
- [x] **Modular Engine Architecture (`src/engine/`):** Full decoupling into `bot_worker.py`, `worker_snapshot.py`, `worker_order_ops.py`, `worker_cycle.py`, `worker_admin.py`, `worker_state.py`.
- [x] **Modular Exchange Architecture (`src/exchange/`):** CCXT execution separated into `live.py`, `live_orders.py`, and self-healing `paper.py`.
- [x] **Protocol 7 Modularity Compliance:** 100% of files in `src/` and `tests/` strictly <= 100 lines.
- [x] **Automated Test Suite:** 160/160 unit and regression tests passing with 100% success rate in 2.39s.

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
   - Hurst Exponent chaos rejection ($H > 0.52$).
   - Market maker inventory depletion frontrunning.
   - Lead-Lag cross-asset latency arbitrage across 35 Halal coins.
   - Cumulative Volume Delta (CVD) anti-spoofing order flow.
   - Bitcoin flash-crash veto gate ($< -0.4\%$).
   - Multi-timeframe (15m) trend alignment filter.
   - Dynamic Market-Adaptive score regulator (70.0 - 85.0 scaling based on BTC macro climate).
   - Ratcheted ladder profit lock with 4 locked profit tiers.
   - Order Book Imbalance (OBI) guard vetoing buy orders into sell walls ($OBI < -0.30$).
   - Interactive 2-Way Telegram Bot commands (`/status`, `/pause`, `/resume`, `/close_all`, `/autopsy`).
   - High-speed offline backtester and parameter optimizer.
   - Anti-slippage shield preventing adverse fills.
   - Lot-size and tick precision sanitization.
   - Asynchronous Telegram mobile notifications.
   - Automated session diagnostic autopsy.
4. **Dynamic Sizing ($5 Min Notional):** Respects Binance limits, auto-calculates concurrent slots.
5. **Dual Mode:** Paper trading default, toggleable to Live with dedicated UI buttons (`#mode-paper-btn` and `#mode-live-btn`).
6. **Mobile Independence:** Continues executing in cloud/server even when phone is powered off.

## 3. Active Sprint Status
- **Current Milestone:** All 5 Institutional Pillars & UI Controls Fully Completed & Verified.
- **Pillar 1: Market-Adaptive Score Regulator:** COMPLETE (`src/core/adaptive_regulator.py`).
- **Pillar 2: Ratcheted Ladder Profit Lock:** COMPLETE (`src/core/risk_manager.py`).
- **Pillar 3: Order Book Imbalance (OBI) Guard:** COMPLETE (`src/exchange/orderbook_depth.py`).
- **Pillar 4: Interactive 2-Way Telegram Bot:** COMPLETE (`src/core/telegram_command_listener.py`).
- **Pillar 5: Fast Offline Backtester & Strategy Optimizer:** COMPLETE (`src/core/backtest_engine.py`, `scripts/run_backtest.py`).
- **UI Mode Switching Buttons:** COMPLETE (`#mode-paper-btn` & `#mode-live-btn` linked to `/api/mode`).
- **Test Verification:** 160/160 automated tests passing with zero errors (100% pass rate).
- **Protocol Compliance:** Zero files exceeding 100 lines across the entire codebase.
