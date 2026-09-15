"""
Unit tests for Institutional Order Flow, FVGs, and Liquidity Sweeps.
"""

import pytest
import pandas as pd
import numpy as np
from app.features.order_flow import calculate_order_flow_features
from app.strategies.institutional_sweep import InstitutionalLiquiditySweepStrategy
from app.broker.models import MarketRegime, SymbolSpecification, TradeSide


def test_fair_value_gap_detection():
    # Construct 3-candle sequence with an aggressive upward impulse gap
    # Candle 0: High = 100.0
    # Candle 1: Strong bull bar (100.2 to 103.0)
    # Candle 2: Low = 101.5 (leaves 1.5 pt gap between candle 2 low and candle 0 high)
    df = pd.DataFrame(
        {
            "open": [99.0, 100.2, 102.0],
            "high": [100.0, 103.0, 103.5],
            "low": [98.5, 100.1, 101.5],
            "close": [99.8, 102.8, 103.0],
            "volume": [100.0, 500.0, 200.0],
        }
    )

    res = calculate_order_flow_features(df)
    assert res["is_bullish_fvg"].iloc[-1] == 1
    assert res["fvg_bullish_level"].iloc[-1] == 101.5


def test_institutional_liquidity_sweep_strategy():
    spec = SymbolSpecification(
        symbol="XAUUSD",
        digits=2,
        lot_min=0.01,
        lot_max=20.0,
        lot_step=0.01,
        contract_size=100.0,
        tick_size=0.01,
        tick_value=1.0,
    )
    strat = InstitutionalLiquiditySweepStrategy()

    # Create 35 bars where the last bar pierces session low and closes with strong rejection
    df = pd.DataFrame(
        {
            "open": [2350.0] * 35,
            "high": [2352.0] * 35,
            "low": [2342.0] * 35,
            "close": [2349.5] * 35,
            "sweep_session_low": [1] * 35,
            "sweep_session_high": [0] * 35,
            "in_bullish_fvg": [0] * 35,
            "in_bearish_fvg": [0] * 35,
            "atr_14": [2.5] * 35,
        }
    )

    sig = strat.evaluate("XAUUSD", df, MarketRegime.RANGING, spec)
    assert sig is not None
    assert sig.side == TradeSide.BUY
    assert sig.take_profit > sig.entry_price
    assert sig.stop_loss < sig.entry_price
    # Check 2.5:1 R:R
    risk = sig.entry_price - sig.stop_loss
    reward = sig.take_profit - sig.entry_price
    assert round(reward / risk, 1) == 2.5
