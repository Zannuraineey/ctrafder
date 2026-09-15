"""
Dynamic Position Sizing & Lot Calculator.
Calculates exact volume based on account equity, risk %, stop loss distance, and instrument specs.
Section 30 of project.md.
"""

from typing import Tuple, Optional
import math
from loguru import logger

from app.broker.models import SymbolSpecification


class LotCalculator:
    """
    Computes mathematically rigorous position sizes strictly governed by risk limits.
    """

    @staticmethod
    def calculate_lot_size(
        balance: float,
        risk_percent: float,
        entry_price: float,
        stop_loss_price: float,
        spec: SymbolSpecification,
        free_margin: float,
    ) -> Tuple[float, float, float, Optional[str]]:
        """
        Calculate allowed volume.
        Returns:
            allowed_lots: float (e.g. 0.08)
            risk_amount: float ($)
            margin_required: float ($)
            veto_reason: Optional[str] (None if valid)
        """
        if balance <= 0:
            return 0.0, 0.0, 0.0, "Account balance is zero or negative"

        risk_amount = balance * risk_percent
        price_distance = abs(entry_price - stop_loss_price)

        if price_distance <= 0:
            return 0.0, 0.0, 0.0, "Stop loss distance is zero"

        # Ticks at risk
        tick_size = max(spec.tick_size, 1e-9)
        ticks_at_risk = price_distance / tick_size

        # Cost per lot in account currency for the given stop distance
        # tick_value is the value of 1 tick movement for 1 standard lot
        cost_per_lot = ticks_at_risk * max(spec.tick_value, 1e-5)

        if cost_per_lot <= 0:
            return 0.0, 0.0, 0.0, "Calculated cost per lot is zero or negative"

        raw_lots = risk_amount / cost_per_lot

        # Step quantization
        step = max(spec.lot_step, 0.001)
        steps_count = math.floor(raw_lots / step)
        quantized_lots = round(steps_count * step, 4)

        # Enforce limits
        if quantized_lots < spec.lot_min:
            # If the minimum lot exceeds allowed risk, reject trade
            min_lot_risk = spec.lot_min * cost_per_lot
            if min_lot_risk > risk_amount * 1.25:  # Allow 25% tolerance for min lots
                return (
                    0.0,
                    risk_amount,
                    0.0,
                    f"Required min lot {spec.lot_min} exceeds max allowable risk (${min_lot_risk:.2f} > ${risk_amount:.2f})",
                )
            quantized_lots = spec.lot_min

        allowed_lots = min(quantized_lots, spec.lot_max)
        allowed_lots = round(allowed_lots, 4)

        # Margin check: Notional value * margin rate
        # For metals/indices/crypto quoted in USD: notional = lots * contract_size * entry_price
        # For EURUSD: notional in USD = lots * contract_size * entry_price
        margin_required = allowed_lots * spec.contract_size * entry_price * spec.margin_rate
        if margin_required > free_margin * 0.80:
            return (
                0.0,
                risk_amount,
                margin_required,
                f"Insufficient free margin. Required: ${margin_required:.2f}, Available: ${free_margin:.2f}",
            )

        actual_risk_amount = allowed_lots * cost_per_lot

        return allowed_lots, round(actual_risk_amount, 2), round(margin_required, 2), None
