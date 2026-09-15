@echo off
title ANTIGRAVITY QUANT // Deriv cTrader Institutional Workstation
color 0A

echo ======================================================================
echo   ANTIGRAVITY QUANTUM // DERIV CTRADER INSTITUTIONAL WORKSTATION
echo ======================================================================
echo.
echo Starting Web Dashboard on http://127.0.0.1:8000 ...
echo Opening your default browser...
echo.

start "" "http://127.0.0.1:8000"

py -3.13 -m uvicorn app.dashboard.server:app --host 127.0.0.1 --port 8000 --no-access-log --reload

pause
