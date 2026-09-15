"""
Double-Barrier Labeling Engine for Machine Learning.
Section 44 of project.md.
"""

from typing import Tuple
import pandas as pd
import numpy as np

from app.learning.labeling import (
    TripleBarrierLabeler,
    compute_meta_labels,
    get_daily_volatility,
    get_vertical_barriers,
)


def compute_double_barrier_labels(
    df: pd.DataFrame,
    horizon_bars: int = 30,
    rr_ratio: float = 2.0,
    atr_multiplier: float = 1.5,
) -> pd.Series:
    """
    Computes outcome-based binary labels using upper (TP) and lower (SL) barriers.
    Returns:
        pd.Series of integer labels:
        1: Take Profit barrier reached first (Win)
        0: Stop Loss barrier reached first or expired (Loss)
    """
    n = len(df)
    labels = np.zeros(n, dtype=int)
    close = df["close"].values
    high = df["high"].values
    low = df["low"].values
    atr = df.get("atr_14", df["high"] - df["low"]).values

    for i in range(n - horizon_bars):
        entry_price = close[i]
        curr_atr = max(atr[i], entry_price * 0.001)

        sl_dist = curr_atr * atr_multiplier
        tp_dist = sl_dist * rr_ratio

        tp_barrier = entry_price + tp_dist
        sl_barrier = entry_price - sl_dist

        outcome = 0
        # Scan forward within horizon
        for j in range(i + 1, min(i + 1 + horizon_bars, n)):
            hit_tp = high[j] >= tp_barrier
            hit_sl = low[j] <= sl_barrier

            if hit_tp and not hit_sl:
                outcome = 1
                break
            elif hit_sl:
                outcome = 0
                break

        labels[i] = outcome

    return pd.Series(labels, index=df.index, name="target")
