"""
Autonomous Quantitative Trading Agent Representation.
Represents an individual trader on the institutional floor with account-tier awareness,
anti-tilt discipline, and penalty box enforcement.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import pandas as pd

from app.broker.models import (
    TradeSignal,
    TradeSide,
    MarketRegime,
    SymbolSpecification,
)
from app.market.deriv_universe import AccountTier
from app.risk.account_tier import AccountTierEngine


class TradingAgent:
    """
    An autonomous algorithmic trader specialized in a specific strategy,
    market regime, asset class, and account tier.
    """

    def __init__(
        self,
        agent_id: int,
        name: str,
        pod_name: str,
        specialized_symbols: Optional[List[str]] = None,
        preferred_regimes: Optional[List[MarketRegime]] = None,
        base_strategy_name: str = "TREND_PULLBACK",
        account_tier_min: AccountTier = AccountTier.MICRO,
    ):
        self.agent_id = agent_id
        self.name = name
        self.pod_name = pod_name
        self.specialized_symbols = specialized_symbols or []
        self.preferred_regimes = preferred_regimes or [
            MarketRegime.TRENDING_UP,
            MarketRegime.TRENDING_DOWN,
        ]
        self.base_strategy_name = base_strategy_name
        self.account_tier_min = account_tier_min

        # Performance Attribution & Risk Metrics
        self.capital_weight: float = 1.0  # Dynamic multiplier from Capital Allocator
        self.trades_count: int = 0
        self.wins_count: int = 0
        self.total_pnl: float = 0.0
        self.rolling_sharpe: float = 1.5
        self.consecutive_losses: int = 0
        self.is_probationary: bool = False

        # Anti-Greed & Penalty Box Tracking
        self.cooldown_until: Optional[datetime] = None
        self.mistakes_count: int = 0
        self.penalty_reason: Optional[str] = None

    @property
    def win_rate(self) -> float:
        if self.trades_count == 0:
            return 0.50
        return round(self.wins_count / self.trades_count, 3)

    def is_in_penalty_box(self) -> bool:
        """Returns True if agent is currently benched for emotional or risk mistakes."""
        if self.cooldown_until and datetime.utcnow() < self.cooldown_until:
            return True
        return False

    def apply_penalty(self, reason: str, minutes: int = 30) -> None:
        """Bench an undisciplined agent, slash capital weight, and enforce cooldown."""
        self.cooldown_until = datetime.utcnow() + timedelta(minutes=minutes)
        self.capital_weight = max(0.25, round(self.capital_weight * 0.50, 2))
        self.mistakes_count += 1
        self.penalty_reason = reason

    def is_active_for_account(self, balance: float) -> bool:
        """Verify if current account equity meets the agent's minimum tier mandate."""
        current_tier = AccountTierEngine.classify_account(balance)
        tier_hierarchy = {
            AccountTier.MICRO: 1,
            AccountTier.SMALL: 2,
            AccountTier.MEDIUM: 3,
            AccountTier.INSTITUTIONAL: 4,
        }
        return tier_hierarchy[current_tier] >= tier_hierarchy[self.account_tier_min]

    def record_trade_outcome(self, pnl: float) -> None:
        """Update agent performance track record."""
        self.trades_count += 1
        self.total_pnl += pnl
        if pnl > 0:
            self.wins_count += 1
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1

    def is_eligible_for_symbol_and_regime(
        self, symbol: str, regime: MarketRegime, current_balance: Optional[float] = None
    ) -> bool:
        """Check if symbol, regime, and account tier match agent's specialized mandate."""
        # Check penalty box
        if self.is_in_penalty_box():
            return False

        # Check account balance tier if provided
        if current_balance is not None and not self.is_active_for_account(current_balance):
            return False

        # Check symbol specialization
        if self.specialized_symbols and symbol not in self.specialized_symbols:
            return False

        # Check regime suitability
        if self.preferred_regimes and regime not in self.preferred_regimes:
            return False

        return True
