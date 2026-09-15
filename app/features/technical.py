"""
Vectorized Technical Analysis Indicators in pure NumPy & Pandas.
Zero C-compiler dependency, fully cross-platform, fast and robust.
"""

import numpy as np
import pandas as pd
from typing import Tuple, Dict


def calculate_ema(series: pd.Series, period: int) -> pd.Series:
    """Calculate Exponential Moving Average."""
    return series.ewm(span=period, adjust=False).mean()


def calculate_sma(series: pd.Series, period: int) -> pd.Series:
    """Calculate Simple Moving Average."""
    return series.rolling(window=period, min_periods=period).mean()


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index (RSI) using Wilder's smoothing."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / (avg_loss + 1e-12)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi.fillna(50.0)


def calculate_macd(
    series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate MACD Line, Signal Line, and Histogram."""
    ema_fast = calculate_ema(series, fast)
    ema_slow = calculate_ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def calculate_atr(
    high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14
) -> pd.Series:
    """Calculate Average True Range (ATR)."""
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    return atr.bfill().fillna(0.0)


def calculate_adx(
    high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate Average Directional Index (ADX), +DI, and -DI."""
    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    tr = pd.concat(
        [high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()],
        axis=1,
    ).max(axis=1)

    atr = tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    plus_dm_s = pd.Series(plus_dm, index=high.index).ewm(
        alpha=1.0 / period, min_periods=period, adjust=False
    ).mean()
    minus_dm_s = pd.Series(minus_dm, index=high.index).ewm(
        alpha=1.0 / period, min_periods=period, adjust=False
    ).mean()

    plus_di = 100.0 * (plus_dm_s / (atr + 1e-12))
    minus_di = 100.0 * (minus_dm_s / (atr + 1e-12))

    dx = 100.0 * (plus_di - minus_di).abs() / ((plus_di + minus_di) + 1e-12)
    adx = dx.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    return adx.fillna(20.0), plus_di.fillna(20.0), minus_di.fillna(20.0)


def calculate_bollinger_bands(
    series: pd.Series, period: int = 20, num_std: float = 2.0
) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series, pd.Series]:
    """
    Calculate Bollinger Bands: Upper, Middle, Lower, Bandwidth, %B.
    """
    middle = calculate_sma(series, period)
    std = series.rolling(window=period, min_periods=period).std()
    upper = middle + (std * num_std)
    lower = middle - (std * num_std)
    bandwidth = (upper - lower) / (middle + 1e-12)
    percent_b = (series - lower) / ((upper - lower) + 1e-12)
    return upper, middle, lower, bandwidth, percent_b


def calculate_stochastic(
    high: pd.Series, low: pd.Series, close: pd.Series, k_period: int = 14, d_period: int = 3
) -> Tuple[pd.Series, pd.Series]:
    """Calculate Stochastic Oscillator %K and %D."""
    lowest_low = low.rolling(window=k_period, min_periods=k_period).min()
    highest_high = high.rolling(window=k_period, min_periods=k_period).max()
    k_line = 100.0 * ((close - lowest_low) / ((highest_high - lowest_low) + 1e-12))
    d_line = k_line.rolling(window=d_period, min_periods=d_period).mean()
    return k_line.fillna(50.0), d_line.fillna(50.0)


def calculate_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """Calculate On-Balance Volume (OBV)."""
    change = close.diff()
    direction = np.where(change > 0, 1.0, np.where(change < 0, -1.0, 0.0))
    obv = (volume * direction).cumsum()
    return obv.fillna(0.0)


def calculate_technical_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add complete technical indicator feature set to DataFrame with open, high, low, close, volume.
    """
    out = df.copy()
    close = out["close"]
    high = out["high"]
    low = out["low"]
    volume = out["volume"] if "volume" in out else pd.Series(0.0, index=out.index)

    # Moving Averages
    out["ema_9"] = calculate_ema(close, 9)
    out["ema_21"] = calculate_ema(close, 21)
    out["ema_50"] = calculate_ema(close, 50)
    out["ema_200"] = calculate_ema(close, 200)
    out["sma_20"] = calculate_sma(close, 20)

    # Distances & Slopes
    out["dist_ema_21"] = (close - out["ema_21"]) / (close + 1e-12)
    out["dist_ema_50"] = (close - out["ema_50"]) / (close + 1e-12)
    out["dist_ema_200"] = (close - out["ema_200"]) / (close + 1e-12)
    out["ema_trend_aligned"] = (
        (out["ema_9"] > out["ema_21"]) & (out["ema_21"] > out["ema_50"])
    ).astype(int) - (
        (out["ema_9"] < out["ema_21"]) & (out["ema_21"] < out["ema_50"])
    ).astype(int)

    # RSI
    out["rsi_14"] = calculate_rsi(close, 14)

    # MACD
    macd, sig, hist = calculate_macd(close, 12, 26, 9)
    out["macd_line"] = macd
    out["macd_signal"] = sig
    out["macd_hist"] = hist

    # ATR & Normalized Volatility
    out["atr_14"] = calculate_atr(high, low, close, 14)
    out["atr_norm"] = out["atr_14"] / (close + 1e-12)

    # ADX
    adx, plus_di, minus_di = calculate_adx(high, low, close, 14)
    out["adx"] = adx
    out["plus_di"] = plus_di
    out["minus_di"] = minus_di

    # Bollinger Bands
    bb_up, bb_mid, bb_low, bb_w, bb_pct = calculate_bollinger_bands(close, 20, 2.0)
    out["bb_upper"] = bb_up
    out["bb_middle"] = bb_mid
    out["bb_lower"] = bb_low
    out["bb_bandwidth"] = bb_w
    out["bb_percent_b"] = bb_pct

    # Stochastic
    stoch_k, stoch_d = calculate_stochastic(high, low, close, 14, 3)
    out["stoch_k"] = stoch_k
    out["stoch_d"] = stoch_d

    # OBV
    out["obv"] = calculate_obv(close, volume)

    return out
