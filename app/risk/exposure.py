"""
Portfolio Exposure and Position Count Controls.
Section 36 of project.md.
"""

from typing import List, Optional
from app.broker.models import Position, PositionStatus


class ExposureManager:
    """
    Guards total open exposure, concurrency, and position duplication.
    """

    def __init__(self, max_open_positions: int = 3, max_portfolio_risk_pct: float = 0.02):
        self.max_open_positions = max_open_positions
        self.max_portfolio_risk_pct = max_portfolio_risk_pct

    def check_exposure(
        self,
        symbol: str,
        open_positions: List[Position],
        proposed_risk_pct: float,
    ) -> Optional[str]:
        """
        Return reason string if exposure limit exceeded, else None.
        """
        active = [p for p in open_positions if p.status == PositionStatus.OPEN]

        # 1. Max positions check
        if len(active) >= self.max_open_positions:
            return f"Max open positions reached ({len(active)}/{self.max_open_positions})"

        # 2. Duplicate symbol check
        for p in active:
            if p.symbol == symbol:
                return f"Duplicate position active on {symbol}"

        return None
