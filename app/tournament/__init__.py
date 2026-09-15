"""
Strategy Tournament & Bayesian Capital Allocation Package.
Alphas compete under walk-forward validation and are dynamically allocated
capital via Multi-Armed Bandit (Thompson Sampling) and Deflated Sharpe Ratio.
"""

from app.tournament.allocator import ThompsonSamplingAllocator, StrategyArm
from app.tournament.metrics import QuantitativeMetricsCalculator
from app.tournament.tournament import StrategyTournamentEngine

__all__ = [
    "ThompsonSamplingAllocator",
    "StrategyArm",
    "QuantitativeMetricsCalculator",
    "StrategyTournamentEngine",
]
