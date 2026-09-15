"""
Vectorized Price Action and Candlestick Pattern Features.
"""

import numpy as np
import pandas as pd


def calculate_price_action_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract candle anatomy and price action characteristics.
    """
    out = df.copy()
    open_p = out["open"]
    high = out["high"]
    low = out["low"]
    close = out["close"]

    # Range and Body
    candle_range = (high - low).clip(lower=1e-9)
    body = (close - open_p).abs()
    body_ratio = body / candle_range

    # Upper & Lower Wicks
    upper_wick = high - np.maximum(open_p, close)
    lower_wick = np.minimum(open_p, close) - low

    upper_wick_ratio = upper_wick / candle_range
    lower_wick_ratio = lower_wick / candle_range

    # Close Location Value (from -1.0 at low to +1.0 at high)
    clv = ((close - low) - (high - close)) / candle_range

    out["candle_range"] = candle_range
    out["body_ratio"] = body_ratio
    out["upper_wick_ratio"] = upper_wick_ratio
    out["lower_wick_ratio"] = lower_wick_ratio
    out["close_location_value"] = clv

    # Momentum / Return
    out["return_1"] = close.pct_change(1).fillna(0.0)
    out["return_3"] = close.pct_change(3).fillna(0.0)
    out["return_5"] = close.pct_change(5).fillna(0.0)

    # Consecutive Directional Bars
    is_bull = (close > open_p).astype(int)
    is_bear = (close < open_p).astype(int)

    # Vectorized consecutive runs
    consec_bull = (is_bull * (is_bull.groupby((is_bull != is_bull.shift()).cumsum()).cumcount() + 1))
    consec_bear = (is_bear * (is_bear.groupby((is_bear != is_bear.shift()).cumsum()).cumcount() + 1))
    out["consecutive_bullish"] = consec_bull
    out["consecutive_bearish"] = consec_bear

    # Candlestick Anatomy Patterns
    # Pin Bar (Long wick rejecting a side, small body)
    out["is_bullish_rejection"] = (
        (lower_wick_ratio > 0.55) & (body_ratio < 0.35) & (upper_wick_ratio < 0.20)
    ).astype(int)

    out["is_bearish_rejection"] = (
        (upper_wick_ratio > 0.55) & (body_ratio < 0.35) & (lower_wick_ratio < 0.20)
    ).astype(int)

    # Bullish/Bearish Engulfing
    prev_body = body.shift(1).fillna(0.0)
    prev_bull = is_bull.shift(1).fillna(0).astype(bool)
    prev_bear = is_bear.shift(1).fillna(0).astype(bool)

    out["is_engulfing_bullish"] = (
        prev_bear & (is_bull == 1) & (body > prev_body) & (close > open_p.shift(1))
    ).astype(int)

    out["is_engulfing_bearish"] = (
        prev_bull & (is_bear == 1) & (body > prev_body) & (close < open_p.shift(1))
    ).astype(int)

    return out
