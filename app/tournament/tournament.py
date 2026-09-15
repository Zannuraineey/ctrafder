"""
Strategy Tournament Engine.
Runs real-time performance competitions among competing quantitative strategies,
computes Deflated Sharpe Ratios, and drives Thompson Sampling capital reallocation.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import numpy as np
from loguru import logger

from app.tournament.allocator import ThompsonSamplingAllocator
from app.tournament.metrics import QuantitativeMetricsCalculator


@dataclass
class TournamentLeaderboardEntry:
    rank: int
    strategy_name: str
    total_trades: int
    win_rate: float
    total_pnl: float
    profit_factor: float
    sharpe_ratio: float
    deflated_sharpe_ratio: float
    max_drawdown: float
    capital_allocation: float
    status: str   # ACTIVE, TOP_PERFORMER, PROBATION, BENCHED


class StrategyTournamentEngine:
    """
    Coordinates strategy competition, evaluation, and Bayesian capital weighting.
    """

    def __init__(self):
        self.allocator = ThompsonSamplingAllocator()
        self.trade_history: Dict[str, List[float]] = {}
        self._initialize_core_strategies()

    def _initialize_core_strategies(self) -> None:
        core_alphas = [
            "POC_REACTION",
            "TREND_PULLBACK",
            "VOLATILITY_BREAKOUT",
            "MOMENTUM_CONTINUATION",
            "FAST_SCALPER",
            "INSTITUTIONAL_SWEEP",
        ]
        for name in core_alphas:
            self.allocator.register_strategy(name)
            self.trade_history[name] = []

    def record_trade(self, strategy_name: str, pnl: float) -> None:
        """Record trade execution result and update Bayesian distribution."""
        self.allocator.record_outcome(strategy_name, pnl)
        self.trade_history.setdefault(strategy_name, []).append(pnl)

    def run_tournament_ranking(self) -> List[TournamentLeaderboardEntry]:
        """
        Evaluate all strategies across statistical metrics and generate ranked leaderboard.
        """
        weights = self.allocator.sample_capital_weights()
        num_strategies = len(self.allocator.arms)
        entries: List[TournamentLeaderboardEntry] = []

        for name, arm in self.allocator.arms.items():
            pnls = self.trade_history.get(name, [])
            n_trades = len(pnls)

            if n_trades > 0:
                wins = sum(1 for p in pnls if p > 0)
                losses = sum(1 for p in pnls if p <= 0)
                win_rate = round(wins / n_trades, 3)
                tot_pnl = round(sum(pnls), 2)
                gross_profit = sum(p for p in pnls if p > 0)
                gross_loss = abs(sum(p for p in pnls if p < 0))
                profit_factor = round(gross_profit / max(gross_loss, 1e-4), 2)

                returns = np.array(pnls) / 1000.0  # Normalized return proxy
                sharpe = QuantitativeMetricsCalculator.calculate_sharpe(returns)
                dsr = QuantitativeMetricsCalculator.calculate_deflated_sharpe(
                    estimated_sharpe=sharpe,
                    num_trials=num_strategies,
                    num_observations=n_trades,
                )
                equity_curve = np.cumsum(pnls) + 1000.0
                mdd = QuantitativeMetricsCalculator.calculate_max_drawdown(equity_curve)
            else:
                win_rate = 0.50
                tot_pnl = 0.0
                profit_factor = 1.0
                sharpe = 0.0
                dsr = 0.50
                mdd = 0.0

            alloc = weights.get(name, 1.0)
            if arm.is_benched:
                status = "BENCHED"
            elif dsr >= 0.70 and alloc >= 1.2:
                status = "TOP_PERFORMER"
            elif win_rate < 0.45:
                status = "PROBATION"
            else:
                status = "ACTIVE"

            entries.append(
                TournamentLeaderboardEntry(
                    rank=0,
                    strategy_name=name,
                    total_trades=n_trades,
                    win_rate=win_rate,
                    total_pnl=tot_pnl,
                    profit_factor=profit_factor,
                    sharpe_ratio=round(sharpe, 2),
                    deflated_sharpe_ratio=round(dsr, 2),
                    max_drawdown=round(mdd * 100.0, 1),
                    capital_allocation=alloc,
                    status=status,
                )
            )

        # Sort by total PnL and Deflated Sharpe Ratio
        entries.sort(key=lambda e: (e.total_pnl, e.deflated_sharpe_ratio), reverse=True)
        for idx, entry in enumerate(entries, start=1):
            entry.rank = idx

        return entries
