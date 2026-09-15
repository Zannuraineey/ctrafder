"""
Market Structure Analysis: Swings, BOS, CHoCH, Liquidity Sweeps, Support/Resistance.
"""

import numpy as np
import pandas as pd
from typing import Tuple


def find_pivots(
    high: pd.Series, low: pd.Series, window: int = 5
) -> Tuple[pd.Series, pd.Series]:
    """
    Detect local swing highs and swing lows using a rolling window.
    """
    swing_high = (
        (high == high.rolling(window * 2 + 1, center=True).max())
    ).astype(float)
    swing_low = (
        (low == low.rolling(window * 2 + 1, center=True).min())
    ).astype(float)

    # Fill NaN from rolling edge
    swing_high = swing_high.fillna(0.0)
    swing_low = swing_low.fillna(0.0)
    return swing_high, swing_low


def calculate_structure_features(df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
    """
    Extract market structure features: pivots, HH/HL/LH/LL, BOS, sweeps, SR levels.
    """
    out = df.copy()
    high = out["high"]
    low = out["low"]
    close = out["close"]

    # Rolling local extrema
    rolling_high = high.rolling(window=window * 2, min_periods=window).max()
    rolling_low = low.rolling(window=window * 2, min_periods=window).min()

    out["swing_high_level"] = rolling_high.shift(1).ffill()
    out["swing_low_level"] = rolling_low.shift(1).ffill()

    # Distances to swing levels (in % of price)
    out["dist_swing_high"] = (out["swing_high_level"] - close) / (close + 1e-12)
    out["dist_swing_low"] = (close - out["swing_low_level"]) / (close + 1e-12)

    # Break of Structure (BOS)
    # Bullish BOS: close breaks above previous swing high
    out["bos_bullish"] = (
        (close > out["swing_high_level"]) & (close.shift(1) <= out["swing_high_level"].shift(1))
    ).astype(int)

    # Bearish BOS: close breaks below previous swing low
    out["bos_bearish"] = (
        (close < out["swing_low_level"]) & (close.shift(1) >= out["swing_low_level"].shift(1))
    ).astype(int)

    # Liquidity Sweeps: Wick pierces previous swing level but close remains inside
    out["liquidity_sweep_high"] = (
        (high > out["swing_high_level"]) & (close < out["swing_high_level"])
    ).astype(int)

    out["liquidity_sweep_low"] = (
        (low < out["swing_low_level"]) & (close > out["swing_low_level"])
    ).astype(int)

    # Structure Regime: Consecutive HH/HL vs LH/LL
    prev_swing_h = out["swing_high_level"]
    prev_swing_l = out["swing_low_level"]

    higher_highs = (prev_swing_h > prev_swing_h.shift(window)).astype(int)
    higher_lows = (prev_swing_l > prev_swing_l.shift(window)).astype(int)
    lower_highs = (prev_swing_h < prev_swing_h.shift(window)).astype(int)
    lower_lows = (prev_swing_l < prev_swing_l.shift(window)).astype(int)

    out["structure_trend"] = np.where(
        (higher_highs == 1) & (higher_lows == 1),
        1,  # Bullish Structure
        np.where((lower_highs == 1) & (lower_lows == 1), -1, 0),  # Bearish Structure
    )

    return out
