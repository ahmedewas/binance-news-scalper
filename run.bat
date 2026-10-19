@echo off
title Binance News Scalper - High Velocity Bot
color 0A
cd /d "%~dp0"

echo ===================================================================
echo     BINANCE NEWS SCALPER - INSTITUTIONAL QUANT ENGINE
echo ===================================================================
echo.
echo [*] Mode: PAPER TRADING (Real Market Data & Live News)
echo [*] Portfolio: $15.00 USDT Initial (3 Slots x $5.00)
echo [*] Strategies: Wyckoff Regime + FVG + CVD + Kelly + Hurst Filter
echo [*] Dashboard PC: http://localhost:8080
echo [*] Dashboard Mobile (Wi-Fi): http://192.168.1.46:8080
echo.
echo ===================================================================
echo [*] Launching Browser Dashboard in 2 seconds...
timeout /t 2 /nobreak >nul
start http://localhost:8080

echo [*] Starting Trading Engine Daemon...
echo [*] Press Ctrl+C at any time to safely stop the bot.
echo ===================================================================
echo.

python run.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] Bot terminated with error code %ERRORLEVEL%
    pause
)
