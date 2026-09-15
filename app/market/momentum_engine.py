"""
Advanced Momentum Engine.
Computes multi-factor institutional momentum score (0-100) and classifies momentum state.
(project.md Section 2, strategy.md Section 2)
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import numpy as np


class MomentumState(str, Enum):
    BUILDING = "BUILDING"
    STRONG = "STRONG"
    ACCELERATING = "ACCELERATING"
    PEAK = "PEAK"
    WEAKENING = "WEAKENING"
    FAILED = "FAILED"
    REVERSED = "REVERSED"


class MomentumTier(str, Enum):
    WEAK = "WEAK"              # 0-30
    DEVELOPING = "DEVELOPING"  # 30-50
    MODERATE = "MODERATE"      # 50-70
    STRONG = "STRONG"          # 70-85
    EXTREME = "EXTREME"        # 85-100


@dataclass
class MomentumMetrics:
    momentum_score: float      # 0 to 100
    tier: MomentumTier
    state: MomentumState
    velocity: float            # Points per candle (first derivative)
    acceleration: float        # Change in velocity (second derivative)
    adx: float
    di_spread: float           # DI+ minus DI-
    rsi_slope: float           # Change in RSI over 3 bars
    macd_hist_accel: float     # MACD histogram slope/acceleration
    body_expansion_ratio: float
    is_favorable_direction: bool
    summary: str


class AdvancedMomentumEngine:
    """
    Computes a comprehensive institutional Momentum Score (0-100),
    incorporating price velocity, acceleration, directional indicators,
    oscillator slopes, and candle expansion.
    """

    @classmethod
    def analyze(
        cls,
        df: pd.DataFrame,
        is_bullish_bias: Optional[bool] = None,
    ) -> MomentumMetrics:
        """
        Extracts multi-factor momentum score and state from candle dataframe.
        """
        if df.empty or len(df) < 8:
            return MomentumMetrics(
                momentum_score=50.0,
                tier=MomentumTier.MODERATE,
                state=MomentumState.BUILDING,
                velocity=0.0,
                acceleration=0.0,
                adx=20.0,
                di_spread=0.0,
                rsi_slope=0.0,
                macd_hist_accel=0.0,
                body_expansion_ratio=1.0,
                is_favorable_direction=True,
                summary="Default baseline momentum",
            )

        high = df["high"].values
        low = df["low"].values
        close = df["close"].values
        open_p = df["open"].values
        n = len(df)

        # 1. Price Velocity & Acceleration (first and second derivatives of price)
        # Velocity over last 3 bars: (Close[-1] - Close[-4]) / 3
        v1 = (close[-1] - close[-2]) if n >= 2 else 0.0
        v2 = (close[-2] - close[-3]) if n >= 3 else 0.0
        v3 = (close[-3] - close[-4]) if n >= 4 else 0.0
        velocity = float((v1 + v2 + v3) / 3.0)
        acceleration = float(v1 - v2)

        # If direction bias is not specified, infer from velocity
        if is_bullish_bias is None:
            is_bullish_bias = velocity >= 0.0

        # 2. ADX and Directional Indicators (+DI, -DI)
        # If technical indicators are already present in df, use them, otherwise compute
        adx_val = float(df["adx"].iloc[-1]) if "adx" in df else 25.0
        di_plus = float(df["di_plus"].iloc[-1]) if "di_plus" in df else 25.0
        di_minus = float(df["di_minus"].iloc[-1]) if "di_minus" in df else 20.0
        di_spread = di_plus - di_minus

        # 3. RSI and RSI Slope
        if "rsi_14" in df:
            rsi_curr = float(df["rsi_14"].iloc[-1])
            rsi_prev = float(df["rsi_14"].iloc[-3]) if n >= 4 else rsi_curr
            rsi_slope = rsi_curr - rsi_prev
        else:
            # Quick 14-bar RSI calculation
            deltas = np.diff(close[-(min(n, 15)):])
            gains = np.maximum(deltas, 0)
            losses = np.abs(np.minimum(deltas, 0))
            avg_g = np.mean(gains) if len(gains) > 0 else 1e-5
            avg_l = np.mean(losses) if len(losses) > 0 else 1e-5
            rs = avg_g / max(avg_l, 1e-6)
            rsi_curr = 100.0 - (100.0 / (1.0 + rs))
            rsi_slope = float(deltas[-1] if len(deltas) > 0 else 0.0)

        # 4. MACD Histogram Acceleration
        if "macd_hist" in df:
            macd_h_curr = float(df["macd_hist"].iloc[-1])
            macd_h_prev = float(df["macd_hist"].iloc[-2]) if n >= 2 else macd_h_curr
            macd_hist_accel = macd_h_curr - macd_h_prev
        else:
            macd_h_curr = 0.0
            macd_hist_accel = float(acceleration)

        # 5. Candle Expansion relative to ATR
        atr = float(df["atr_14"].iloc[-1]) if "atr_14" in df else max(float(np.mean(high[-10:] - low[-10:])), 1e-6)
        curr_body = abs(close[-1] - open_p[-1])
        body_expansion_ratio = round(curr_body / max(atr, 1e-6), 2)

        # 6. Directional Alignment
        if is_bullish_bias:
            is_favorable = (velocity > 0) and (di_spread >= -5)
        else:
            is_favorable = (velocity < 0) and (di_spread <= 5)

        # 7. Composite Momentum Score Calculation (0 - 100)
        # Factor A: Trend Strength / ADX (0-25 pts)
        adx_pts = min(25.0, (adx_val / 40.0) * 25.0)

        # Factor B: DI Separation aligned with bias (0-25 pts)
        if is_bullish_bias:
            di_alignment = np.clip((di_spread + 10.0) / 30.0, 0.0, 1.0)
        else:
            di_alignment = np.clip((-di_spread + 10.0) / 30.0, 0.0, 1.0)
        di_pts = float(di_alignment * 25.0)

        # Factor C: RSI Momentum and Slope (0-20 pts)
        if is_bullish_bias:
            rsi_level_pts = 10.0 if (45.0 <= rsi_curr <= 72.0) else (5.0 if rsi_curr > 72 else 2.0)
            rsi_slope_pts = 10.0 if rsi_slope > 1.5 else (6.0 if rsi_slope >= 0 else 1.0)
        else:
            rsi_level_pts = 10.0 if (28.0 <= rsi_curr <= 55.0) else (5.0 if rsi_curr < 28 else 2.0)
            rsi_slope_pts = 10.0 if rsi_slope < -1.5 else (6.0 if rsi_slope <= 0 else 1.0)
        rsi_pts = rsi_level_pts + rsi_slope_pts

        # Factor D: Acceleration & Candle Expansion (0-30 pts)
        accel_aligned = (acceleration > 0) if is_bullish_bias else (acceleration < 0)
        accel_pts = 15.0 if accel_aligned else 5.0

        if body_expansion_ratio >= 1.2:
            expansion_pts = 15.0
        elif body_expansion_ratio >= 0.8:
            expansion_pts = 10.0
        else:
            expansion_pts = 4.0

        total_score = adx_pts + di_pts + rsi_pts + accel_pts + expansion_pts
        if not is_favorable:
            # When velocity/direction opposes trade bias, momentum in trade direction is crushed
            total_score = min(total_score * 0.45, 28.0)

        momentum_score = float(np.clip(total_score, 5.0, 98.0))
        momentum_score = round(momentum_score, 1)

        # 8. Tier Classification
        if momentum_score >= 85.0:
            tier = MomentumTier.EXTREME
        elif momentum_score >= 70.0:
            tier = MomentumTier.STRONG
        elif momentum_score >= 50.0:
            tier = MomentumTier.MODERATE
        elif momentum_score >= 30.0:
            tier = MomentumTier.DEVELOPING
        else:
            tier = MomentumTier.WEAK

        # 9. Momentum State Classification
        if not is_favorable:
            if (is_bullish_bias and velocity < -0.05) or (not is_bullish_bias and velocity > 0.05):
                state = MomentumState.REVERSED
            else:
                state = MomentumState.FAILED
        elif (is_bullish_bias and acceleration < -abs(velocity * 0.5)) or (not is_bullish_bias and acceleration > abs(velocity * 0.5)):
            if momentum_score >= 75.0:
                state = MomentumState.PEAK
            else:
                state = MomentumState.WEAKENING
        elif momentum_score >= 70.0:
            is_accel = (is_bullish_bias and acceleration > 0) or (not is_bullish_bias and acceleration < 0)
            state = MomentumState.ACCELERATING if is_accel else MomentumState.STRONG
        elif momentum_score >= 50.0:
            state = MomentumState.BUILDING
        elif momentum_score < 35.0:
            state = MomentumState.FAILED
        else:
            state = MomentumState.WEAKENING

        summary = (
            f"Score: {momentum_score}/100 ({tier.value}) | State: {state.value} | "
            f"ADX: {adx_val:.1f} | DI Spread: {di_spread:+.1f} | Velocity: {velocity:+.4f}"
        )

        return MomentumMetrics(
            momentum_score=momentum_score,
            tier=tier,
            state=state,
            velocity=round(velocity, 5),
            acceleration=round(acceleration, 5),
            adx=round(adx_val, 2),
            di_spread=round(di_spread, 2),
            rsi_slope=round(rsi_slope, 2),
            macd_hist_accel=round(macd_hist_accel, 4),
            body_expansion_ratio=body_expansion_ratio,
            is_favorable_direction=is_favorable,
            summary=summary,
        )
