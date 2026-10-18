# Living Memory & Project State Tracking: Binance News Scalper

## 1. Locked Working Modules (قائمة الخطوط الحمراء)
- [x] **Lead-Lag Cross-Asset Correlator (`src/core/lead_lag_correlator.py`):** Latency arbitrage exploiting sector lag (SOL->JUP/RAY, FET->RENDER/NEAR, BTC->ETH/SOL).
- [x] **Cumulative Volume Delta Tracker (`src/core/cvd_tracker.py`):** Aggressive taker buy/sell order flow analysis, rejecting spoofing.
- [x] **Multi-Factor Scoring Engine (`src/core/scoring_engine.py`):** Market Regime + Momentum + Volume Spike + News Sentiment + CVD Order Flow with strict Bull Trap protection.
- [x] **Dynamic Portfolio Allocator (`src/core/portfolio_allocator.py`):** Dynamically sizes slots according to liquid USDT and Binance Min Notional ($5 USDT):
  - $10 balance -> 2 slots of $5 each.
  - $15 balance -> 3 slots of $5 each.
  - Scales automatically up to 5 slots.
- [x] **Dynamic Triple-Exit Manager (`src/core/risk_manager.py`):** Trailing Take-Profit (+1.2% activation, 0.4% trailing offset), Hard Stop-Loss (-0.9%), and Time-Out (20 mins recycling).
- [x] **Dual-Mode Exchange Layer (`src/exchange/`):**
  - `PaperExchange`: Live price feeds without credentials, simulated 0.1% spot fees.
  - `LiveExchange`: CCXT Binance Spot interface with full error shielding.
- [x] **News Radar & NLP Analyzer (`src/news/`):** Real-time crypto feeds with regex ticker extraction and sentiment scoring.
- [x] **24/7 Background Trading Worker (`src/engine/`):** Independent daemon running continuously regardless of client connection.
- [x] **Mobile PWA Dashboard (`src/web/`):** Dark mode, responsive web UI with one-click toggles and emergency exit.
- [x] **100-Line Modularity Compliance:** 100% of codebase files strictly <= 100 lines.
- [x] **Automated Test Suite:** 22/22 unit and regression tests passing with 100% success rate.
- [x] **Cloud-Native Deployment Assets:** `Dockerfile`, `Procfile`, and `koyeb.yaml` ready.
- [x] **GitHub Remote Repository:** Cleanly committed and pushed to `https://github.com/ahmedewas/binance-news-scalper` (branch: `main`).

## 2. Checkpoint for Next Session (نقطة الاستئناف للجلسة القادمة)
- **Status:** Project code is 100% complete, tested, and pushed to GitHub.
- **Immediate Next Step:** Log into Render dashboard (`dashboard.render.com/login`), connect the `ahmedewas/binance-news-scalper` repository, select Frankfurt region, and deploy to obtain the 24/7 mobile web URL.
