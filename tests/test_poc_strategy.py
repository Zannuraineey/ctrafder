"""
Tests for Volume Profile Point of Control (POC) Reaction Strategy & Multi-Pair Paper Simulator.
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime

from app.broker.models import SymbolSpecification, TradeSide, MarketRegime
from app.strategies.poc_strategy import POCReactionStrategy, compute_volume_profile
from app.backtest.poc_simulation import POCPaperSimulator


def test_compute_volume_profile():
    """Verify that the highest volume price node is identified as POC."""
    highs = np.array([100.0, 101.0, 102.0, 101.5, 100.5])
    lows = np.array([99.0, 99.5, 100.5, 100.0, 99.2])
    closes = np.array([99.8, 100.5, 101.0, 100.8, 100.1])
    # Massive volume clustered around 100.5 - 101.0
    volumes = np.array([50.0, 500.0, 800.0, 450.0, 60.0])

    poc, vah, val = compute_volume_profile(highs, lows, closes, volumes, digits=2, num_bins=20)

    assert poc >= 99.5 and poc <= 101.5
    assert vah >= poc
    assert val <= poc


def test_poc_reaction_bullish_support_bounce():
    """Verify that when price tests POC from above and rejects lower prices, a BUY signal is produced."""
    strategy = POCReactionStrategy()
    spec = SymbolSpecification(
        symbol="XAUUSD",
        asset_class="METALS",
        digits=2,
        tick_size=0.01,
        tick_value=1.0,
        lot_min=0.01,
        lot_max=20.0,
    )

    # Generate 30 bars where POC establishes around 2350.0
    bars = []
    base = 2350.0
    for i in range(25):
        bars.append({
            "open": base,
            "high": base + 1.5,
            "low": base - 1.5,
            "close": base + 0.2,
            "volume": 500.0,
            "atr_14": 2.0,
        })

    # Add bar testing POC support: dips to 2349.5 (POC is ~2350), bounces and closes at 2352.0
    bars.append({
        "open": 2350.5,
        "high": 2352.2,
        "low": 2349.4,
        "close": 2352.0,
        "volume": 600.0,
        "atr_14": 2.0,
    })

    df = pd.DataFrame(bars)
    signal = strategy.evaluate(symbol="XAUUSD", features_df=df, regime=MarketRegime.RANGING, spec=spec)

    assert signal is not None
    assert signal.side == TradeSide.BUY
    assert signal.stop_loss < signal.entry_price
    assert signal.take_profit > signal.entry_price
    assert signal.metadata.get("setup") == "POC_SUPPORT_BOUNCE"


def test_poc_reaction_bearish_resistance_rejection():
    """Verify that when price tests POC from below and rejects higher prices, a SELL signal is produced."""
    strategy = POCReactionStrategy()
    spec = SymbolSpecification(
        symbol="EURUSD",
        asset_class="FOREX",
        digits=5,
        tick_size=0.00001,
        tick_value=1.0,
        lot_min=0.01,
        lot_max=50.0,
    )

    # Generate bars where POC settles around 1.08500
    bars = []
    base = 1.08500
    for i in range(25):
        bars.append({
            "open": base,
            "high": base + 0.00080,
            "low": base - 0.00080,
            "close": base - 0.00010,
            "volume": 400.0,
            "atr_14": 0.00100,
        })

    # Add bar testing POC resistance: rallies to 1.08520, rejects and closes at 1.08430
    bars.append({
        "open": 1.08460,
        "high": 1.08530,
        "low": 1.08420,
        "close": 1.08430,
        "volume": 650.0,
        "atr_14": 0.00100,
    })

    df = pd.DataFrame(bars)
    signal = strategy.evaluate(symbol="EURUSD", features_df=df, regime=MarketRegime.RANGING, spec=spec)

    assert signal is not None
    assert signal.side == TradeSide.SELL
    assert signal.stop_loss > signal.entry_price
    assert signal.take_profit < signal.entry_price
    assert signal.metadata.get("setup") == "POC_RESISTANCE_REJECTION"


def test_poc_paper_simulation_and_ranking():
    """Verify that the multi-pair POC paper simulator ranks pairs by profitability."""
    simulator = POCPaperSimulator(starting_balance=100.0, risk_per_trade=0.03)

    symbols = ["XAUUSD", "Vol_25_1s", "EURUSD", "Step_Index"]
    res = simulator.run_multi_pair_simulation(symbols=symbols)

    assert "rankings" in res
    assert len(res["rankings"]) == len(symbols)
    assert res["top_profitable_symbol"] != ""

    # Verify descending order of total_profit
    profits = [r["total_profit"] for r in res["rankings"]]
    assert profits == sorted(profits, reverse=True)

    # Verify ranks are numbered 1, 2, 3, 4
    ranks = [r["rank"] for r in res["rankings"]]
    assert ranks == [1, 2, 3, 4]
