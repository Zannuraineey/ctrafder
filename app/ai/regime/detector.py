"""
Market Regime Detector.
Classifies market state into TRENDING_UP, TRENDING_DOWN, RANGING, BREAKOUT,
HIGH_VOLATILITY, LOW_VOLATILITY, or CHOPPY.
"""

from typing import Tuple
import pandas as pd
import numpy as np

from app.broker.models import MarketRegime


class RegimeDetector:
    """
    Classifies market conditions using multi-factor indicators and structure.
    """

    @classmethod
    def detect_regime(cls, features_df: pd.DataFrame) -> Tuple[MarketRegime, float]:
        """
        Classify market regime and return (MarketRegime, confidence_score).
        """
        if features_df.empty or len(features_df) < 20:
            return MarketRegime.UNKNOWN, 0.0

        curr = features_df.iloc[-1]
        recent = features_df.iloc[-10:]

        adx = curr.get("adx", 20.0)
        atr_pct = curr.get("atr_percentile", 0.5)
        bandwidth = curr.get("bb_bandwidth", 0.05)
        ema_aligned = curr.get("ema_trend_aligned", 0)
        close = curr["close"]
        ema_50 = curr.get("ema_50", close)
        ema_200 = curr.get("ema_200", close)
        bos_bull = curr.get("bos_bullish", 0)
        bos_bear = curr.get("bos_bearish", 0)
        expansion = curr.get("volatility_expansion_ratio", 1.0)

        # 1. Check for BREAKOUT regime
        if (bos_bull == 1 or bos_bear == 1) and expansion > 1.25 and bandwidth > 0.04:
            confidence = min(0.95, 0.65 + (expansion - 1.0) * 0.3)
            return MarketRegime.BREAKOUT, round(confidence, 2)

        # 2. Check for EXTREME / HIGH VOLATILITY
        if atr_pct > 0.88 or expansion > 1.8:
            return MarketRegime.HIGH_VOLATILITY, 0.85

        # 3. Check for STRONG TRENDS
        if adx > 24.0:
            if ema_aligned == 1 and close > ema_50:
                confidence = min(0.95, 0.60 + (adx / 100.0) * 0.5)
                return MarketRegime.TRENDING_UP, round(confidence, 2)
            elif ema_aligned == -1 and close < ema_50:
                confidence = min(0.95, 0.60 + (adx / 100.0) * 0.5)
                return MarketRegime.TRENDING_DOWN, round(confidence, 2)

        # 4. Check for CHOPPY / WHIPSAW MARKET
        # Low ADX + frequent alternation between bullish and bearish candles
        if adx < 16.0 and bandwidth < 0.025:
            return MarketRegime.LOW_VOLATILITY, 0.80

        if adx < 19.0:
            # Check candle overlap in recent 6 bars
            recent_ranges = (recent["high"] - recent["low"]).clip(lower=1e-9)
            overlap_count = 0
            for i in range(1, len(recent)):
                prev_bar = recent.iloc[i - 1]
                curr_bar = recent.iloc[i]
                overlap = min(prev_bar["high"], curr_bar["high"]) - max(prev_bar["low"], curr_bar["low"])
                if overlap > 0:
                    overlap_count += 1

            if overlap_count >= 5:
                return MarketRegime.CHOPPY, 0.75
            else:
                return MarketRegime.RANGING, 0.70

        # Default: If above EMA50, mild trend up, else mild trend down
        if close > ema_50:
            return MarketRegime.TRENDING_UP, 0.55
        else:
            return MarketRegime.TRENDING_DOWN, 0.55
