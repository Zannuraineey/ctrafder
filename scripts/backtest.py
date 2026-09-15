"""
Backtest Execution Script.
"""

from app.database import init_db
from app.broker.models import SymbolSpecification
from app.backtest.engine import BacktestEngine
from main import generate_synthetic_candles

if __name__ == "__main__":
    init_db()
    symbol = "XAUUSD"
    print(f"Running backtest for {symbol}...")
    candles = generate_synthetic_candles(symbol, count=500, base_price=2350.0)
    spec = SymbolSpecification(
        symbol=symbol,
        digits=2,
        lot_min=0.01,
        lot_max=20.0,
        lot_step=0.01,
        contract_size=100.0,
        tick_size=0.01,
        tick_value=1.0,
    )
    engine = BacktestEngine(starting_balance=10000.0)
    result = engine.run(candles, spec=spec)
    print("Backtest Metrics:")
    for k, v in result["metrics"].items():
        print(f"  {k}: {v}")
