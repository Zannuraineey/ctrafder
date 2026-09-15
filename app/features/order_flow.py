"""
Institutional Order Flow, Liquidity Pools, FVGs, and Volume Profile.
Tracks Asian session sweeps, Previous Day High/Low (PDH/PDL), Fair Value Gaps, and POC/VAH/VAL.
"""

from typing import Tuple, Dict, Any, List
import pandas as pd
import numpy as np


def calculate_order_flow_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract institutional order flow, liquidity sweeps, and Fair Value Gaps.
    """
    out = df.copy()
    high = out["high"]
    low = out["low"]
    close = out["close"]
    open_p = out["open"]
    volume = out["volume"] if "volume" in out else pd.Series(100.0, index=out.index)

    # 1. Fair Value Gaps (FVG) - 3-bar imbalance detection
    # Bullish FVG: candle i low > candle i-2 high (uncontested bullish impulse gap)
    prev_high_2 = high.shift(2)
    bullish_fvg = (low > prev_high_2) & (close.shift(1) > open_p.shift(1))
    fvg_top_bull = np.where(bullish_fvg, low, np.nan)
    fvg_bot_bull = np.where(bullish_fvg, prev_high_2, np.nan)

    # Bearish FVG: candle i high < candle i-2 low (uncontested bearish impulse gap)
    prev_low_2 = low.shift(2)
    bearish_fvg = (high < prev_low_2) & (close.shift(1) < open_p.shift(1))
    fvg_top_bear = np.where(bearish_fvg, prev_low_2, np.nan)
    fvg_bot_bear = np.where(bearish_fvg, high, np.nan)

    out["is_bullish_fvg"] = bullish_fvg.astype(int)
    out["is_bearish_fvg"] = bearish_fvg.astype(int)
    out["fvg_bullish_level"] = pd.Series(fvg_top_bull, index=out.index).ffill()
    out["fvg_bearish_level"] = pd.Series(fvg_bot_bear, index=out.index).ffill()

    # In-FVG test (Price currently resting within recent FVG mitigation zone)
    out["in_bullish_fvg"] = (
        (close >= out["fvg_bullish_level"] * 0.998) & (close <= out["fvg_bullish_level"] * 1.002)
    ).astype(int)
    out["in_bearish_fvg"] = (
        (close >= out["fvg_bearish_level"] * 0.998) & (close <= out["fvg_bearish_level"] * 1.002)
    ).astype(int)

    # 2. Session Liquidity Levels: Rolling High/Low (Proxy for Session/Day levels)
    # 24-hour lookback proxy (~1440 bars in 1m, or 48 bars in 30m)
    session_window = max(1, min(len(df), 240))
    min_p_sess = max(1, min(session_window, 30))
    session_high = high.rolling(window=session_window, min_periods=min_p_sess).max()
    session_low = low.rolling(window=session_window, min_periods=min_p_sess).min()

    out["session_high"] = session_high.shift(1).ffill()
    out["session_low"] = session_low.shift(1).ffill()

    # 3. Liquidity Sweeps of Session High / Low
    # Bullish Liquidity Sweep (Turtle Soup buy): Low pierces session low, but bar closes back inside
    clv = (
        out["close_location_value"]
        if "close_location_value" in out
        else ((close - low) - (high - close)) / (high - low).clip(lower=1e-9)
    )
    out["sweep_session_low"] = (
        (low < out["session_low"]) & (close > out["session_low"]) & (clv > 0.25)
    ).astype(int)

    # Bearish Liquidity Sweep (Turtle Soup sell): High pierces session high, but bar closes back inside
    out["sweep_session_high"] = (
        (high > out["session_high"]) & (close < out["session_high"]) & (clv < -0.25)
    ).astype(int)

    # 4. Volume Profile: Point of Control (POC) & Value Area (VAH / VAL 70%)
    # Computes genuine volume-at-price distribution using multi-bin histogram
    def compute_volume_profile_poc_va(sub_high, sub_low, sub_close, sub_vol) -> Tuple[float, float, float]:
        if len(sub_close) < 5:
            last_c = float(sub_close.iloc[-1])
            return last_c, last_c * 1.002, last_c * 0.998
        min_p = float(sub_low.min())
        max_p = float(sub_high.max())
        if max_p <= min_p or np.isnan(min_p) or np.isnan(max_p):
            last_c = float(sub_close.iloc[-1])
            return last_c, last_c * 1.002, last_c * 0.998

        num_bins = 20
        bins = np.linspace(min_p, max_p, num_bins + 1)
        bin_vols = np.zeros(num_bins)

        # Distribute volume into price bins across the full candle price range
        for h, l, c, v in zip(sub_high, sub_low, sub_close, sub_vol):
            vol = max(float(v), 1.0)
            low_idx = int(np.clip(np.digitize(l, bins) - 1, 0, num_bins - 1))
            high_idx = int(np.clip(np.digitize(h, bins) - 1, 0, num_bins - 1))
            if low_idx == high_idx:
                bin_vols[low_idx] += vol
            else:
                span = max(high_idx - low_idx + 1, 1)
                bin_vols[low_idx : high_idx + 1] += vol / span

        poc_idx = int(np.argmax(bin_vols))
        poc_price = (bins[poc_idx] + bins[poc_idx + 1]) / 2.0

        # Value Area (70% highest volume surrounding POC)
        total_vol = max(float(np.sum(bin_vols)), 1.0)
        target_vol = total_vol * 0.70
        curr_vol = bin_vols[poc_idx]
        left_idx = poc_idx
        right_idx = poc_idx

        while curr_vol < target_vol and (left_idx > 0 or right_idx < num_bins - 1):
            left_v = bin_vols[left_idx - 1] if left_idx > 0 else 0.0
            right_v = bin_vols[right_idx + 1] if right_idx < num_bins - 1 else 0.0
            if left_v >= right_v and left_idx > 0:
                left_idx -= 1
                curr_vol += left_v
            elif right_idx < num_bins - 1:
                right_idx += 1
                curr_vol += right_v
            else:
                break

        val_price = bins[left_idx]
        vah_price = bins[right_idx + 1]
        return float(poc_price), float(vah_price), float(val_price)

    # Calculate rolling volume profile across rolling windows (60-period window)
    poc_series = []
    vah_series = []
    val_series = []
    n_rows = len(out)
    w_size = min(n_rows, 60)

    # For speed and consistency, compute over rolling blocks
    step = 5
    last_poc, last_vah, last_val = None, None, None
    for i in range(n_rows):
        if i < 10:
            p_val = close.iloc[i]
            last_poc, last_vah, last_val = p_val, p_val * 1.002, p_val * 0.998
        elif i % step == 0 or i == n_rows - 1 or last_poc is None:
            start_i = max(0, i - w_size)
            last_poc, last_vah, last_val = compute_volume_profile_poc_va(
                high.iloc[start_i : i + 1],
                low.iloc[start_i : i + 1],
                close.iloc[start_i : i + 1],
                volume.iloc[start_i : i + 1],
            )
        poc_series.append(last_poc)
        vah_series.append(last_vah)
        val_series.append(last_val)

    out["vp_poc"] = poc_series
    out["vp_vah"] = vah_series
    out["vp_val"] = val_series

    return out

