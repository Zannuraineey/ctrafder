# Antigravity Deriv cTrader Institutional Quantitative Platform

An institutional-grade, multi-agent AI quantitative trading workstation designed for the complete **Deriv 57-instrument multi-asset catalog** (Synthetics, Crash/Boom, Step, Range Break, Jump, Metals, Commodities, Forex).

---

## ⚡ Quick Start: How to Run the Software

You can launch the platform immediately with **1-Click Launchers** or via the **Command Line (CLI)**:

### 1. 1-Click Launchers (Windows)
Double-click either file in the project folder:
- **`run_dashboard.bat`**: Starts the Visual Web Workstation and opens your browser at **[http://127.0.0.1:8000](http://127.0.0.1:8000)**.
  - *Inside the Web Workstation, click the vibrant green **`[▶ START AUTO-TRADING]`** button in the top navigation bar to start live scanning and 100-agent execution! Click **`[⏹ STOP AUTO-TRADING]`** to pause at any time.*
- **`run_trading.bat`**: Starts the autonomous 100-agent live paper trading engine in the terminal.

### 2. Command Line (PowerShell / CMD)
```powershell
# Navigate to directory
cd c:\Users\lenovo\ctrader

# Install dependencies (first time only)
pip install -r requirements.txt

# Launch the Visual Web Workstation
python main.py dashboard --port 8000

# OR launch live automated paper trading
python main.py run --mode paper

# Check small account ($50) safety advice
python main.py small-account-advice --balance 50
```

---

## 📖 Complete Documentation & User Manual

For the complete, comprehensive manual covering:
- Step-by-step installation and virtual environment setup
- High-density Dark Glassmorphic Web Workstation interface guide
- Deriv small account ($10–$500) rules: Safe vs. Blowout pairs matrix
- 100-Trader Multi-Agent Pod Floor architecture
- Anti-Greed Mistake Engine & Penalty Box rules
- Full CLI command reference
- Connecting live Deriv cTrader via OAuth 2.0
- Running unit tests and troubleshooting

👉 **Please refer to the comprehensive manual: [HOW_TO_RUN.md](file:///c:/Users/lenovo/ctrader/HOW_TO_RUN.md)**.

---

## 🧪 Automated Integrity Tests
To verify all 31 institutional risk, agent consensus, and execution tests:
```powershell
python -m pytest -v
```
**Expected Result**: `31 passed in ~4.3s` (100% Green).
