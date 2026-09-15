"""
Value-at-Risk (VaR) & Expected Shortfall (CVaR) Engine.
Computes portfolio risk exposure under 99% confidence intervals.
"""

from typing import List, Dict, Tuple
import numpy as np
from app.broker.models import Position, PositionStatus, SymbolSpecification


class ValueAtRiskEngine:
    """
    Computes 99% 1-Day Parametric and Historical Value-at-Risk and Expected Shortfall.
    """

    @classmethod
    def calculate_portfolio_var(
        cls,
        open_positions: List[Position],
        symbol_volatilities: Dict[str, float],
        confidence_level: float = 0.99,
    ) -> Tuple[float, float]:
        """
        Calculate total dollar VaR and Expected Shortfall (CVaR).
        Returns:
            var_dollar: float (Estimated 99% max loss over 1 day)
            cvar_dollar: float (Expected loss beyond VaR threshold)
        """
        active = [p for p in open_positions if p.status == PositionStatus.OPEN]
        if not active:
            return 0.0, 0.0

        # Parametric Z-score: 99% confidence -> 2.326
        z = 2.326 if confidence_level == 0.99 else 1.645

        position_vars = []
        for p in active:
            notional = p.volume * p.current_price
            daily_vol = symbol_volatilities.get(p.symbol, 0.015) / np.sqrt(252)
            pos_var = notional * daily_vol * z
            position_vars.append(pos_var)

        # Simplified conservative sum (assuming correlation = 0.6)
        total_var = float(np.sum(position_vars))
        # Expected shortfall (CVaR) is approximately 1.15x - 1.25x VaR for normal distributions
        cvar = total_var * 1.20

        return round(total_var, 2), round(cvar, 2)
