"""
Tests for Institutional Triple-Barrier Labeling and Meta-Labeling.
"""

import pytest
import numpy as np
import pandas as pd

from app.learning.labeling import (
    get_daily_volatility,
    get_vertical_barriers,
    TripleBarrierLabeler,
    compute_meta_labels,
)


def _generate_synthetic_df(n: int = 100, trend: float = 0.0) -> pd.DataFrame:
    np.random.seed(42)
    prices = [100.0]
    for i in range(1, n):
        step = np.random.normal(trend, 0.5)
        prices.append(max(prices[-1] + step, 1.0))
    
    close = np.array(prices)
    high = close + np.random.uniform(0.1, 0.4, size=n)
    low = close - np.random.uniform(0.1, 0.4, size=n)
    dates = pd.date_range("2026-01-01", periods=n, freq="1min")

    return pd.DataFrame(
        {
            "close": close,
            "high": high,
            "low": low,
        },
        index=dates,
    )


def test_get_daily_volatility():
    df = _generate_synthetic_df(50)
    vol = get_daily_volatility(df["close"], span=20)
    assert len(vol) == 50
    assert (vol > 0).all()
    assert not vol.isna().any()


def test_get_vertical_barriers():
    df = _generate_synthetic_df(50)
    t1 = get_vertical_barriers(df.index, num_bars=10)
    assert len(t1) == 50
    assert t1.iloc[0] == df.index[10]
    assert t1.iloc[45] == df.index[49]  # Clamped to last


def test_triple_barrier_bullish_run():
    # Strong upward trend should trigger TP
    n = 60
    close = np.linspace(100, 150, n)
    high = close + 0.5
    low = close - 0.2
    dates = pd.date_range("2026-01-01", periods=n, freq="1min")
    df = pd.DataFrame({"close": close, "high": high, "low": low}, index=dates)

    labeler = TripleBarrierLabeler(pt_multiplier=1.0, sl_multiplier=1.0, horizon_bars=15)
    events = labeler.apply_barriers(df)

    assert len(events) == n
    # Early bars during strong up-trend should hit TP
    early_bins = events["bin"].iloc[:10]
    assert (early_bins == 1).all()
    assert (events["touch_type"].iloc[:10] == "TP").all()


def test_triple_barrier_bearish_run():
    # Strong downward trend should trigger SL for long positions
    n = 60
    close = np.linspace(100, 50, n)
    high = close + 0.2
    low = close - 0.5
    dates = pd.date_range("2026-01-01", periods=n, freq="1min")
    df = pd.DataFrame({"close": close, "high": high, "low": low}, index=dates)

    labeler = TripleBarrierLabeler(pt_multiplier=1.0, sl_multiplier=1.0, horizon_bars=15)
    events = labeler.apply_barriers(df)

    # Early bars during strong selloff should hit SL
    early_bins = events["bin"].iloc[:10]
    assert (early_bins == -1).all()
    assert (events["touch_type"].iloc[:10] == "SL").all()


def test_triple_barrier_short_side():
    # Downward trend with short side (+1 profit when price falls)
    n = 60
    close = np.linspace(100, 50, n)
    high = close + 0.2
    low = close - 0.5
    dates = pd.date_range("2026-01-01", periods=n, freq="1min")
    df = pd.DataFrame({"close": close, "high": high, "low": low}, index=dates)

    side = pd.Series(-1, index=dates)
    labeler = TripleBarrierLabeler(pt_multiplier=1.0, sl_multiplier=1.0, horizon_bars=15)
    events = labeler.apply_barriers(df, side=side)

    # For short side, price drop hits TP
    early_bins = events["bin"].iloc[:10]
    assert (early_bins == 1).all()
    assert (events["touch_type"].iloc[:10] == "TP").all()


def test_compute_meta_labels():
    events = pd.DataFrame(
        {
            "ret": [0.02, -0.015, 0.01, -0.03, 0.0],
            "bin": [1, -1, 1, -1, 0],
            "touch_type": ["TP", "SL", "TP", "SL", "VERTICAL"],
            "barrier_hit_bar": [3, 2, 5, 1, 15],
        }
    )
    # Case 1: Primary predictions aligned with returns
    # Row 0: ret > 0, pred = 1 -> match! (1)
    # Row 1: ret < 0, pred = -1 -> short made money! (1)
    # Row 2: ret > 0, pred = -1 -> short lost money! (0)
    # Row 3: ret < 0, pred = 1 -> long lost money! (0)
    # Row 4: ret = 0, pred = 1 -> scratch/no profit! (0)
    primary_preds = np.array([1, -1, -1, 1, 1])

    meta = compute_meta_labels(events, primary_preds)

    assert list(meta.values) == [1, 1, 0, 0, 0]
