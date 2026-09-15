"""
Volatility Engine: ATR percentiles, realized volatility, compression/expansion.
"""

import numpy as np
import pandas as pd


def calculate_volatility_features(
    df: pd.DataFrame, window: int = 20, percentile_window: int = 100
) -> pd.DataFrame:
    """
    Extract volatility metrics and regime classifications.
    """
    out = df.copy()
    close = out["close"]
    high = out["high"]
    low = out["low"]

    # True Range
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # Rolling ATR
    atr = tr.rolling(window=window, min_periods=window).mean()
    out["vol_atr"] = atr

    # ATR Percentile Rank over historical lookback
    atr_percentile = (
        atr.rolling(window=percentile_window, min_periods=min(30, percentile_window))
        .apply(lambda s: (s.iloc[-1] - s.min()) / (s.max() - s.min() + 1e-12), raw=False)
        .fillna(0.5)
    )
    out["atr_percentile"] = atr_percentile

    # Realized Volatility of Log Returns
    log_returns = np.log(close / close.shift(1).clip(lower=1e-9)).fillna(0.0)
    realized_vol = log_returns.rolling(window=window, min_periods=window).std() * np.sqrt(252 * 1440)
    out["realized_volatility"] = realized_vol.fillna(0.0)

    # Range Expansion / Contraction Ratio (short ATR / long ATR)
    long_atr = tr.rolling(window=window * 3, min_periods=window).mean()
    out["volatility_expansion_ratio"] = (atr / (long_atr + 1e-12)).fillna(1.0)

    # Volatility Regime Categorization (0: LOW, 1: NORMAL, 2: HIGH, 3: EXTREME)
    out["volatility_regime_code"] = np.where(
        out["atr_percentile"] < 0.20,
        0,  # LOW
        np.where(
            out["atr_percentile"] < 0.70,
            1,  # NORMAL
            np.where(out["atr_percentile"] < 0.90, 2, 3),  # HIGH or EXTREME
        ),
    )

    return out
