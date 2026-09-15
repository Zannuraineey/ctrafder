"""
Institutional Triple-Barrier Method & Meta-Labeling Engine.
Based on Marcos Lopez de Prado's 'Advances in Financial Machine Learning' (AFML Ch. 3).

Provides:
1. Dynamic volatility estimation (rolling standard deviation of log returns / EWMA).
2. Triple-barrier labeling (upper horizontal TP, lower horizontal SL, vertical timeout t_1).
3. Primary multi-class label generation (-1, 0, 1).
4. Secondary meta-labeling for model bet sizing and probability calibration (0 or 1).
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
from loguru import logger


def get_daily_volatility(
    close: pd.Series,
    span: int = 100,
) -> pd.Series:
    """
    Computes dynamic daily volatility using exponentially weighted moving standard deviation
    of log returns, following de Prado AFML Snippet 3.1.
    """
    log_ret = np.log(close / close.shift(1)).fillna(0.0)
    vol = log_ret.ewm(span=span).std()
    # Fill leading NaNs with the first non-zero volatility or a small default epsilon
    vol = vol.bfill()
    vol = vol.replace(0.0, 1e-4)
    return vol


def get_vertical_barriers(
    timestamps: pd.DatetimeIndex,
    num_bars: int = 30,
) -> pd.Series:
    """
    Computes vertical barrier expiration timestamps (t_1) for each event.
    If timestamps is an integer index or RangeIndex, adds num_bars.
    """
    if isinstance(timestamps, pd.DatetimeIndex):
        t1 = pd.Series(index=timestamps, dtype="datetime64[ns]")
        n = len(timestamps)
        for i in range(n):
            target_idx = min(i + num_bars, n - 1)
            t1.iloc[i] = timestamps[target_idx]
        return t1
    else:
        # Generic index fallback
        idx = list(timestamps)
        t1_list = [idx[min(i + num_bars, len(idx) - 1)] for i in range(len(idx))]
        return pd.Series(t1_list, index=timestamps)


class TripleBarrierLabeler:
    """
    Institutional Triple-Barrier Labeling System.
    Evaluates paths against:
    - Barrier 1: Upper horizontal barrier (entry_price * (1 + pt * vol))
    - Barrier 2: Lower horizontal barrier (entry_price * (1 - sl * vol))
    - Barrier 3: Vertical barrier (time expiration after horizon_bars)
    """

    def __init__(
        self,
        pt_multiplier: float = 2.0,
        sl_multiplier: float = 1.0,
        horizon_bars: int = 30,
        min_return: float = 0.0005,
    ):
        self.pt_multiplier = float(pt_multiplier)
        self.sl_multiplier = float(sl_multiplier)
        self.horizon_bars = int(horizon_bars)
        self.min_return = float(min_return)

    def apply_barriers(
        self,
        df: pd.DataFrame,
        side: Optional[pd.Series] = None,
    ) -> pd.DataFrame:
        """
        Applies triple barriers to the price series in df.
        
        df must contain ['close', 'high', 'low'].
        side: Optional series of trade direction (+1 for long, -1 for short).
              If None, standard long-oriented directional barriers are computed.

        Returns DataFrame with columns:
        - 'ret': Path return at earliest touched barrier
        - 'bin': Primary label (+1: TP touched first, -1: SL touched first, 0: vertical timeout)
        - 'touch_type': 'TP', 'SL', or 'VERTICAL'
        - 'barrier_hit_bar': Index offset where barrier was touched
        """
        n = len(df)
        close = df["close"].values
        high = df["high"].values
        low = df["low"].values
        
        # Volatility
        vol = get_daily_volatility(df["close"]).values

        returns = np.zeros(n, dtype=float)
        bins = np.zeros(n, dtype=int)
        touch_types = ["NONE"] * n
        hit_bars = np.zeros(n, dtype=int)

        side_arr = side.values if side is not None else np.ones(n, dtype=int)

        for i in range(n - 1):
            entry_price = close[i]
            curr_vol = max(vol[i], self.min_return)
            s = 1 if side_arr[i] >= 0 else -1

            # Symmetrical barriers adjusted for position side
            pt_dist = entry_price * curr_vol * self.pt_multiplier
            sl_dist = entry_price * curr_vol * self.sl_multiplier

            upper_barrier = entry_price + (pt_dist if s == 1 else sl_dist)
            lower_barrier = entry_price - (sl_dist if s == 1 else pt_dist)

            end_j = min(i + 1 + self.horizon_bars, n)
            touched = False

            for j in range(i + 1, end_j):
                curr_high = high[j]
                curr_low = low[j]

                # Check barrier hits based on side
                if s == 1:
                    hit_tp = curr_high >= upper_barrier
                    hit_sl = curr_low <= lower_barrier
                else:
                    hit_tp = curr_low <= lower_barrier
                    hit_sl = curr_high >= upper_barrier

                if hit_tp and not hit_sl:
                    returns[i] = (upper_barrier / entry_price - 1.0) * s
                    bins[i] = 1
                    touch_types[i] = "TP"
                    hit_bars[i] = j - i
                    touched = True
                    break
                elif hit_sl and not hit_tp:
                    returns[i] = (lower_barrier / entry_price - 1.0) * s
                    bins[i] = -1
                    touch_types[i] = "SL"
                    hit_bars[i] = j - i
                    touched = True
                    break
                elif hit_tp and hit_sl:
                    # Ambiguous bar: conservative stance counts as loss
                    returns[i] = -curr_vol * self.sl_multiplier
                    bins[i] = -1
                    touch_types[i] = "SL"
                    hit_bars[i] = j - i
                    touched = True
                    break

            if not touched:
                # Vertical timeout reached
                exit_idx = end_j - 1
                exit_price = close[exit_idx]
                ret = (exit_price / entry_price - 1.0) * s
                returns[i] = ret
                hit_bars[i] = exit_idx - i
                touch_types[i] = "VERTICAL"
                if abs(ret) < self.min_return:
                    bins[i] = 0
                else:
                    bins[i] = 1 if ret > 0 else -1

        out = pd.DataFrame(
            {
                "ret": returns,
                "bin": bins,
                "touch_type": touch_types,
                "barrier_hit_bar": hit_bars,
            },
            index=df.index,
        )
        return out


def compute_meta_labels(
    triple_barrier_events: pd.DataFrame,
    primary_predictions: Union[pd.Series, np.ndarray],
) -> pd.Series:
    """
    Computes secondary meta-labels for trade sizing and confidence calibration.
    de Prado AFML Snippet 3.8.
    
    Given primary predictions y_star in {-1, 1}:
    - Meta-label = 1 if primary prediction agreed with the sign of the return (profitable trade)
    - Meta-label = 0 if primary prediction resulted in a loss or timeout scratch

    Returns:
        pd.Series of binary labels (0 or 1) aligned with triple_barrier_events.index.
    """
    preds = np.asarray(primary_predictions)
    if len(preds) != len(triple_barrier_events):
        raise ValueError(
            f"Length mismatch: primary_predictions has {len(preds)}, "
            f"events has {len(triple_barrier_events)}"
        )

    ret = triple_barrier_events["ret"].values
    meta_labels = np.zeros(len(triple_barrier_events), dtype=int)

    for i in range(len(triple_barrier_events)):
        pred = preds[i]
        actual_ret = ret[i]

        # Meta-label is 1 if trade made positive return in the predicted direction
        # If prediction is 0 (neutral / pass), no bet was taken -> 0
        if pred != 0 and (actual_ret * (1 if pred > 0 else -1) > 0):
            meta_labels[i] = 1
        else:
            meta_labels[i] = 0

    return pd.Series(meta_labels, index=triple_barrier_events.index, name="meta_label")
