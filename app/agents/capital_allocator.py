"""
Sharpe-Weighted Dynamic Capital Allocator.
Dynamically scales trader risk budgets based on rolling performance and drawdown.
"""

from typing import List
import numpy as np
from loguru import logger

from app.agents.agent import TradingAgent


class CapitalAllocator:
    """
    Allocates risk capital across the floor of 100 traders based on institutional merit.
    """

    @classmethod
    def reallocate_capital(cls, agents: List[TradingAgent]) -> None:
        """
        Recompute capital multipliers for all agents based on win rate,
        consecutive losses, and total P&L.
        """
        for a in agents:
            # 1. Consecutive Loss Defense (Probationary rule)
            if a.consecutive_losses >= 3:
                a.is_probationary = True
                a.capital_weight = 0.35  # Throttle risk to 35% of standard
                continue

            # 2. Performance-based scaling
            wr = a.win_rate
            if a.trades_count >= 5:
                if wr >= 0.65:
                    a.capital_weight = 1.40  # Top performer bonus (+40% capital)
                    a.is_probationary = False
                elif wr >= 0.50:
                    a.capital_weight = 1.00  # Baseline
                    a.is_probationary = False
                else:
                    a.capital_weight = 0.60  # Underperforming (-40% capital)
            else:
                a.capital_weight = 1.00  # Default initial weight
