@echo off
title ANTIGRAVITY QUANT // Live Paper Trading Engine
color 0B

echo ======================================================================
echo   ANTIGRAVITY QUANTUM // LIVE AI TRADING ENGINE (PAPER MODE)
echo ======================================================================
echo.
echo Launching 100-Agent Floor, Account Tier Filter, and Real-Time Dashboard...
echo Press CTRL+C at any time to gracefully halt the engine.
echo.

py -3.13 main.py run --mode paper

pause
