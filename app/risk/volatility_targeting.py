"""
Institutional Volatility Targeting Engine.
Scales position sizes inversely to market realized volatility to maintain constant dollar variance.
"""

from typing import Optional
import numpy as np


class VolatilityTargetingEngine:
    """
    Computes volatility-adjusted sizing multipliers.
    """

    def __init__(self, target_annualized_vol: float = 0.15):
        self.target_annualized_vol = target_annualized_vol  # 15% target portfolio volatility

    def compute_volatility_multiplier(
        self, realized_annualized_vol: float
    ) -> float:
        """
        Returns sizing multiplier (0.30 to 1.80).
        """
        vol = max(realized_annualized_vol, 0.05)
        raw_mult = self.target_annualized_vol / vol
        # Clamp multiplier to avoid extreme under/oversizing
        return float(np.clip(raw_mult, 0.35, 1.75))
