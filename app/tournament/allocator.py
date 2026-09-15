"""
Bayesian Thompson Sampling Capital Allocator.
Dynamically reallocates capital across trading strategies using a Multi-Armed Bandit
with Beta-Bernoulli conjugate priors and exponential memory decay.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import numpy as np
from loguru import logger


@dataclass
class StrategyArm:
    name: str
    alpha: float = 2.0               # Prior successes (Win count)
    beta: float = 2.0                # Prior failures (Loss count)
    total_trades: int = 0
    total_pnl: float = 0.0
    capital_weight: float = 1.0      # Multiplier (0.1x to 3.0x)
    is_benched: bool = False

    @property
    def expected_win_rate(self) -> float:
        return self.alpha / (self.alpha + self.beta)


class ThompsonSamplingAllocator:
    """
    Multi-Armed Bandit allocating risk budgets across strategies
    by sampling from the posterior distribution of strategy returns.
    """

    def __init__(self, decay_factor: float = 0.98, min_weight: float = 0.20, max_weight: float = 2.50):
        self.decay_factor = decay_factor
        self.min_weight = min_weight
        self.max_weight = max_weight
        self.arms: Dict[str, StrategyArm] = {}

    def register_strategy(self, name: str, prior_alpha: float = 2.0, prior_beta: float = 2.0) -> None:
        if name not in self.arms:
            self.arms[name] = StrategyArm(name=name, alpha=prior_alpha, beta=prior_beta)

    def record_outcome(self, strategy_name: str, pnl: float) -> None:
        """
        Update posterior parameters for the strategy with exponential forgetting.
        """
        self.register_strategy(strategy_name)
        arm = self.arms[strategy_name]

        # Apply memory decay to discount ancient history in non-stationary markets
        arm.alpha = 1.0 + (arm.alpha - 1.0) * self.decay_factor
        arm.beta = 1.0 + (arm.beta - 1.0) * self.decay_factor

        # Update with new observation
        if pnl > 0:
            arm.alpha += 1.0
        else:
            arm.beta += 1.0

        arm.total_trades += 1
        arm.total_pnl += pnl

        # Auto-bench arm if expected win rate drops below statistical significance
        if arm.total_trades >= 15 and arm.expected_win_rate < 0.35:
            arm.is_benched = True
        else:
            arm.is_benched = False

    def sample_capital_weights(self, n_samples: int = 1000) -> Dict[str, float]:
        """
        Draw samples from each arm's posterior Beta distribution,
        and normalize into dynamic capital multipliers centered at 1.0x.
        """
        if not self.arms:
            return {}

        active_arms = {k: v for k, v in self.arms.items() if not v.is_benched}
        if not active_arms:
            return {k: self.min_weight for k in self.arms}

        sampled_probas: Dict[str, float] = {}
        for name, arm in active_arms.items():
            # Draw Thompson samples from Beta(alpha, beta)
            samples = np.random.beta(arm.alpha, arm.beta, size=n_samples)
            sampled_probas[name] = float(np.mean(samples))

        # Scale relative to 50% neutral expectation baseline
        baseline = 0.50
        weights: Dict[str, float] = {}
        for name, arm in self.arms.items():
            if arm.is_benched:
                weights[name] = self.min_weight
            else:
                p = sampled_probas[name]
                raw_mult = p / baseline
                weights[name] = round(float(np.clip(raw_mult, self.min_weight, self.max_weight)), 2)
            arm.capital_weight = weights[name]

        return weights
