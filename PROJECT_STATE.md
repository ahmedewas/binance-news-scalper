# Living Memory & Project State Tracking: Binance News Scalper

## 1. Locked Working Modules (قائمة الخطوط الحمراء)
- [x] **Multi-Stage Asymmetric Scale-Out (`src/core/risk_manager.py` & `src/engine/position_handler.py`):** 50% partial take-profit at +1.2%, locking fees and riding the remaining 50% with trailing stop.
- [x] **Preemptive Volume Decay Detector (`src/core/volume_decay_exit.py`):** Early exit if trade volume collapses by >75% after 3 minutes, liberating capital without waiting 20 minutes.
- [x] **Modular Execution Decoupling (`src/engine/opportunity_executor.py` & `position_handler.py`):** Clean separation of entry evaluation and exit execution keeping all worker files strictly <= 100 lines.
- [x] **Direct Binance Announcements Engine (`src/news/binance_announcements.py`):** Sub-second CMS polling for instant new listings and launchpools.
- [x] **Semantic Catalyst Classifier (`src/news/semantic_scorer.py`):** Institutional tier ranking (Tier-1 Listing, Tier-2 Partner) with negation and rumor filter.
- [x] **Cryptographic Dedup Ring-Buffer (`src/news/dedup_buffer.py`):** SHA-256 fingerprinting for 0ms duplicate execution.
- [x] **Smart Money FVG Detector (`src/core/fvg_detector.py`):** 3-candle institutional liquidity imbalance and Fair Value Gap expansion detection.
- [x] **Wyckoff Volume Absorption (`src/core/volume_exhaustion.py`):** Order absorption wicks (Springs) and distribution upthrust wicks (UTADs).
- [x] **Institutional Regime Engine (`src/core/regime_detector.py`):** Multi-timeframe trend synthesized with FVG imbalances and Wyckoff Springs.
- [x] **Fractional Kelly Sizer (`src/core/kelly_sizer.py`):** Asymmetric bet sizing allocating higher capital to ultra-high conviction setups.
- [x] **Hurst Exponent Chaos Filter (`src/core/hurst_filter.py`):** Fractal dimension analysis rejecting Brownian noise ($H < 0.45$) and trading only persistent memory ($H > 0.52$).
- [x] **Market Maker Inventory Depletion Frontrun (`src/core/mm_inventory_frontrun.py`):** Frontrunning MM upward repricing when ask depth is depleted by aggressive market buying.
- [x] **Breakeven Velocity Capital Unlock (`src/core/risk_manager.py` & `portfolio_allocator.py`):** Auto-locking stop at entry + fee coverage at +0.6% gain, freeing up capital slot for instant re-allocation.
- [x] **Lead-Lag Cross-Asset Correlator (`src/core/lead_lag_correlator.py`):** Latency arbitrage exploiting sector lag (SOL->JUP/RAY, FET->RENDER/NEAR, BTC->ETH/SOL).
- [x] **Cumulative Volume Delta Tracker (`src/core/cvd_tracker.py`):** Aggressive taker buy/sell order flow analysis, rejecting spoofing.
- [x] **Multi-Factor Scoring Engine (`src/core/scoring_engine.py`):** Market Regime + Momentum + Volume Spike + News Sentiment + CVD + Hurst + MM Depletion.
- [x] **Dynamic Portfolio Allocator (`src/core/portfolio_allocator.py`):** Dynamically sizes slots according to liquid USDT and Binance Min Notional ($5 USDT):
  - $10 balance -> 2 slots of $5 each.
  - $15 balance -> 3 slots of $5 each.
  - Scales automatically up to 5 slots.
- [x] **Dual-Mode Exchange Layer (`src/exchange/`):**
  - `PaperExchange`: Live price feeds without credentials, simulated 0.1% spot fees.
  - `LiveExchange`: CCXT Binance Spot interface with full error shielding.
- [x] **24/7 Background Trading Worker (`src/engine/`):** Independent daemon running continuously regardless of client connection.
- [x] **Mobile PWA Dashboard (`src/web/`):** Dark mode, responsive web UI with one-click toggles and emergency exit.
- [x] **100-Line Modularity Compliance:** 100% of codebase files strictly <= 100 lines.
- [x] **Automated Test Suite:** 51/51 unit and regression tests passing with 100% success rate.
- [x] **GitHub Remote Repository:** Synced with `https://github.com/ahmedewas/binance-news-scalper` (branch: `main`).

## 2. Cumulative Requirements Registry (سجل المتطلبات التراكمية)
1. **Spot Only:** No leverage, zero liquidation risk.
2. **Capital Velocity:** Multi-stage 50% partial exit, early volume decay recycling, and 20-min max trade lifespan.
3. **Institutional Alpha Edge:**
   - Multi-stage 50% scale-out with free-ride trailing stop.
   - Preemptive volume decay exit before 20-min timeout.
   - Sub-second direct Binance CMS listing announcements scanner.
   - Contextual semantic catalyst classification (Tier 1-3) with negation defense.
   - SHA-256 cryptographic headline deduplication.
   - SMC Fair Value Gap (FVG) liquidity void expansion.
   - Wyckoff Volume Absorption (Springs) and Distribution Upthrusts (UTAD).
   - Fractional Kelly Criterion sizing based on empirical edge.
   - Hurst Exponent chaos rejection.
   - Market maker inventory depletion frontrunning.
   - Lead-Lag cross-asset latency arbitrage.
   - Cumulative Volume Delta (CVD) anti-spoofing order flow.
4. **Dynamic Sizing ($5 Min Notional):** Respects Binance limits, auto-calculates concurrent slots.
5. **Dual Mode:** Paper trading default, toggleable to Live.
6. **Mobile Independence:** Continues executing in cloud even when phone is powered off.

## 3. Active Sprint Status
- **Status:** Part 4 (Execution & Asymmetric Scale-Out Engine) fully verified.
- **Verification:** 51/51 unit tests passed. All files <= 100 lines.
- **Next Step:** Ready for Part 5 review (Web Dashboard, Mobile PWA & Local Interactive Run).
