"""
Whipsaw & False-Breakout Detection Engine.
Calculates the probability that an apparent setup is likely to fail or quickly reverse.
"""

from typing import Dict, Any
import pandas as pd
import numpy as np

from app.broker.models import TradeSide, MarketRegime


class WhipsawDetector:
    """
    Dedicated analyzer for detecting choppy, trap, or high-failure setups.
    """

    @classmethod
    def calculate_whipsaw_probability(
        cls,
        features_df: pd.DataFrame,
        candidate_side: TradeSide,
        regime: MarketRegime,
    ) -> float:
        """
        Calculate whipsaw probability (0.0 = safe/clean, 1.0 = extreme whipsaw risk).
        """
        if features_df.empty or len(features_df) < 15:
            return 0.50

        curr = features_df.iloc[-1]
        recent = features_df.iloc[-8:]

        risk_factors: float = 0.0
        total_weight: float = 0.0

        # 1. ADX Weakness Check
        # In a trend setup, weak ADX signals lack of institutional follow-through
        adx = curr.get("adx", 20.0)
        if adx < 18.0:
            risk_factors += 0.25
        elif adx < 22.0:
            risk_factors += 0.12
        total_weight += 0.25

        # 2. Candle Overlap
        # High overlap between consecutive candles indicates indecision / consolidation chop
        overlaps = 0
        for i in range(1, len(recent)):
            p = recent.iloc[i - 1]
            c = recent.iloc[i]
            overlap_range = min(p["high"], c["high"]) - max(p["low"], c["low"])
            candle_span = max(p["high"] - p["low"], 1e-9)
            if overlap_range / candle_span > 0.40:
                overlaps += 1

        overlap_ratio = overlaps / (len(recent) - 1)
        risk_factors += overlap_ratio * 0.25
        total_weight += 0.25

        # 3. Momentum Disagreement (Divergence indicator)
        rsi = curr.get("rsi_14", 50.0)
        macd_hist = curr.get("macd_hist", 0.0)
        if candidate_side == TradeSide.BUY:
            # Buying when RSI is overbought or MACD histogram is dropping
            if rsi > 70.0:
                risk_factors += 0.15
            if macd_hist < 0:
                risk_factors += 0.10
        elif candidate_side == TradeSide.SELL:
            # Selling when RSI is oversold or MACD histogram is rising
            if rsi < 30.0:
                risk_factors += 0.15
            if macd_hist > 0:
                risk_factors += 0.10
        total_weight += 0.25

        # 4. Recent False Breakout / Liquidity Sweep
        # If the market just had a liquidity sweep against the proposed direction
        has_recent_sweep = (
            (recent["liquidity_sweep_high"] == 1).any()
            if candidate_side == TradeSide.BUY
            else (recent["liquidity_sweep_low"] == 1).any()
        )
        if has_recent_sweep:
            risk_factors += 0.20
        total_weight += 0.25

        # 5. Regime Penalty
        regime_penalty = 0.0
        if regime == MarketRegime.CHOPPY:
            regime_penalty = 0.35
        elif regime == MarketRegime.HIGH_VOLATILITY:
            regime_penalty = 0.15

        raw_prob = (risk_factors / total_weight) + regime_penalty
        return round(float(np.clip(raw_prob, 0.02, 0.98)), 3)
