"""
Volume Pressure and Participation Engine.
Evaluates whether price moves have genuine institutional fuel and directional participation.
(project.md Section 1, strategy.md Section 1)
"""

from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import numpy as np


class VolumeState(str, Enum):
    ACCUMULATING = "ACCUMULATING"
    EXPANDING = "EXPANDING"
    CONFIRMING = "CONFIRMING"
    DECLINING = "DECLINING"
    EXHAUSTING = "EXHAUSTING"


@dataclass
class VolumePressureMetrics:
    rvol: float
    volume_z_score: float
    volume_acceleration: float
    buying_pressure_ratio: float  # 0.0 (all selling) to 1.0 (all buying)
    participation_score: float   # 0 to 100
    volume_state: VolumeState
    is_exhaustion_detected: bool
    is_confirming_direction: bool
    summary: str


class VolumePressureEngine:
    """
    Analyzes volume dynamics, relative volume, pressure distribution,
    and identifies institutional accumulation vs. volume exhaustion.
    """

    LOOKBACK_PERIOD: int = 20

    @classmethod
    def analyze(
        cls,
        df: pd.DataFrame,
        lookback: int = 20,
    ) -> VolumePressureMetrics:
        """
        Calculates institutional volume pressure metrics from OHLCV candles.
        """
        if df.empty or len(df) < 5:
            return VolumePressureMetrics(
                rvol=1.0,
                volume_z_score=0.0,
                volume_acceleration=0.0,
                buying_pressure_ratio=0.5,
                participation_score=50.0,
                volume_state=VolumeState.CONFIRMING,
                is_exhaustion_detected=False,
                is_confirming_direction=True,
                summary="Insufficient candle history for volume pressure",
            )

        high = df["high"].values
        low = df["low"].values
        close = df["close"].values
        open_p = df["open"].values
        volume = df["volume"].values if "volume" in df else np.full(len(df), 100.0)

        n = len(df)
        window = min(n, lookback)
        recent_vols = volume[-window:]
        mean_vol = max(float(np.mean(recent_vols)), 1e-6)
        std_vol = float(np.std(recent_vols))
        current_vol = float(volume[-1])

        # 1. Relative Volume (RVOL)
        rvol = round(current_vol / mean_vol, 2)

        # 2. Volume Z-Score
        z_score = round((current_vol - mean_vol) / max(std_vol, 1e-6), 2)

        # 3. Volume Acceleration (d^2V / dt^2 proxy over last 3 bars)
        if n >= 3:
            d_vol_1 = volume[-1] - volume[-2]
            d_vol_2 = volume[-2] - volume[-3]
            acceleration = float((d_vol_1 - d_vol_2) / mean_vol)
        else:
            acceleration = 0.0
        acceleration = round(acceleration, 2)

        # 4. Directional Buying vs Selling Pressure (Close Location Value + Body direction)
        # CLV = ((Close - Low) - (High - Close)) / (High - Low)
        rng = np.maximum(high[-window:] - low[-window:], 1e-9)
        clv = ((close[-window:] - low[-window:]) - (high[-window:] - close[-window:])) / rng
        
        # Weighted buying volume: bars closing in upper half get more buying weight
        buy_weight = np.clip((clv + 1.0) / 2.0, 0.0, 1.0)
        recent_weights = np.linspace(0.6, 1.0, window)  # Give higher recency weight
        
        weighted_buy_vol = np.sum(recent_vols * buy_weight * recent_weights)
        total_vol_weight = np.sum(recent_vols * recent_weights)
        buying_pressure_ratio = round(float(weighted_buy_vol / max(total_vol_weight, 1e-9)), 2)

        # 5. Price-Volume Confirmation & Candle Expansion
        body_sizes = np.abs(close[-window:] - open_p[-window:])
        mean_body = max(float(np.mean(body_sizes)), 1e-9)
        curr_body = abs(close[-1] - open_p[-1])
        is_body_expanded = curr_body > mean_body * 1.1

        # Direction of latest candle
        is_bullish_bar = close[-1] >= open_p[-1]
        is_confirming_direction = (
            (is_bullish_bar and buying_pressure_ratio >= 0.48)
            or (not is_bullish_bar and buying_pressure_ratio <= 0.52)
        )

        # 6. Volume Exhaustion / Divergence Detection
        # Climax volume (Z-score > 2.2 or RVOL > 2.5) with small body or large opposing wick
        wick_upper = high[-1] - max(open_p[-1], close[-1])
        wick_lower = min(open_p[-1], close[-1]) - low[-1]
        full_range = max(high[-1] - low[-1], 1e-9)
        opposing_wick_ratio = (wick_upper / full_range) if is_bullish_bar else (wick_lower / full_range)

        # Severe volume drying up on new extremes (low RVOL < 0.6 while attempting breakout)
        volume_drying = rvol < 0.65
        climax_exhaustion = (rvol > 2.3 or z_score > 2.2) and (opposing_wick_ratio > 0.45 or curr_body < mean_body * 0.5)

        is_exhaustion_detected = bool(climax_exhaustion or (volume_drying and curr_body > mean_body * 1.5))

        # 7. Volume State Classification
        if is_exhaustion_detected:
            volume_state = VolumeState.EXHAUSTING
        elif rvol > 1.6 and acceleration > 0.3:
            volume_state = VolumeState.EXPANDING
        elif rvol >= 1.0 and is_confirming_direction:
            volume_state = VolumeState.CONFIRMING
        elif rvol < 0.8 and acceleration < -0.2:
            volume_state = VolumeState.DECLINING
        else:
            volume_state = VolumeState.ACCUMULATING

        # 8. Composite Participation Score (0 to 100)
        # Strong participation rewards healthy RVOL (1.2 - 2.5), confirmation, and lack of exhaustion
        score_parts = []
        
        # RVOL contribution (up to 35 pts)
        if rvol >= 2.5:
            score_parts.append(25.0)  # slightly penalized for extreme climax
        elif rvol >= 1.4:
            score_parts.append(35.0)
        elif rvol >= 1.0:
            score_parts.append(28.0)
        elif rvol >= 0.7:
            score_parts.append(18.0)
        else:
            score_parts.append(10.0)

        # Confirmation contribution (up to 30 pts)
        if is_confirming_direction:
            conf_bonus = 30.0 * (1.0 - abs(0.5 - buying_pressure_ratio))  # higher if decisive
            score_parts.append(max(15.0, conf_bonus))
        else:
            score_parts.append(8.0)

        # Acceleration contribution (up to 20 pts)
        if acceleration > 0.2:
            score_parts.append(20.0)
        elif acceleration >= 0.0:
            score_parts.append(14.0)
        elif acceleration >= -0.3:
            score_parts.append(8.0)
        else:
            score_parts.append(2.0)

        # Exhaustion penalty (-30 pts)
        if is_exhaustion_detected:
            score_parts.append(-30.0)
        else:
            score_parts.append(15.0)

        participation_score = float(np.clip(sum(score_parts), 0.0, 100.0))
        participation_score = round(participation_score, 1)

        summary = (
            f"RVOL: {rvol}x | Z-Score: {z_score} | Acceleration: {acceleration:+.2f} | "
            f"Buy/Sell Pressure: {int(buying_pressure_ratio*100)}% | State: {volume_state.value}"
        )

        return VolumePressureMetrics(
            rvol=rvol,
            volume_z_score=z_score,
            volume_acceleration=acceleration,
            buying_pressure_ratio=buying_pressure_ratio,
            participation_score=participation_score,
            volume_state=volume_state,
            is_exhaustion_detected=is_exhaustion_detected,
            is_confirming_direction=is_confirming_direction,
            summary=summary,
        )
