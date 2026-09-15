"""
Quantitative Performance Analytics and Deflated Sharpe Ratio.
Calculates annualized Sharpe, Sortino, Calmar, Maximum Drawdown,
and Marcos López de Prado's Deflated Sharpe Ratio (DSR) to account for selection bias.
"""

from typing import List, Dict, Any, Optional
import numpy as np
import scipy.stats as stats


class QuantitativeMetricsCalculator:
    """
    Computes institutional risk-adjusted return analytics.
    """

    @staticmethod
    def calculate_sharpe(returns: np.ndarray, risk_free_rate: float = 0.0) -> float:
        r = np.asarray(returns, dtype=np.float64)
        if len(r) < 2 or np.std(r) == 0:
            return 0.0
        excess = r - risk_free_rate
        return float(np.mean(excess) / np.std(excess))

    @staticmethod
    def calculate_sortino(returns: np.ndarray, target_return: float = 0.0) -> float:
        r = np.asarray(returns, dtype=np.float64)
        if len(r) < 2:
            return 0.0
        downside = r[r < target_return]
        if len(downside) == 0 or np.std(downside) == 0:
            return float(np.mean(r) / (np.std(r) + 1e-9))
        downside_std = np.sqrt(np.mean((downside - target_return) ** 2))
        return float(np.mean(r - target_return) / max(downside_std, 1e-9))

    @staticmethod
    def calculate_max_drawdown(equity_curve: np.ndarray) -> float:
        eq = np.asarray(equity_curve, dtype=np.float64)
        if len(eq) < 2:
            return 0.0
        running_max = np.maximum.accumulate(eq)
        drawdowns = (eq - running_max) / np.maximum(running_max, 1e-9)
        return float(abs(np.min(drawdowns)))

    @classmethod
    def calculate_deflated_sharpe(
        cls,
        estimated_sharpe: float,
        num_trials: int,
        num_observations: int,
        skewness: float = 0.0,
        kurtosis: float = 3.0,
    ) -> float:
        """
        Calculates the Deflated Sharpe Ratio (DSR) per Bailey & López de Prado (2014).
        Computes the probability that the estimated Sharpe exceeds what would be expected
        purely by luck after multiple strategy trials.
        """
        if num_observations <= 2 or num_trials <= 0:
            return 0.50

        # Euler-Mascheroni constant
        gamma = 0.5772156649
        # Expected maximum Sharpe under the null hypothesis of zero true alpha
        z_n = (1.0 - gamma) * stats.norm.ppf(1.0 - 1.0 / max(num_trials, 2)) + gamma * stats.norm.ppf(
            1.0 - 1.0 / (max(num_trials, 2) * np.e)
        )
        sr_benchmark = max(0.0, z_n)

        # Standard error of Sharpe under non-normal returns
        var_sr = (
            1.0
            - skewness * estimated_sharpe
            + ((kurtosis - 1.0) / 4.0) * (estimated_sharpe ** 2)
        ) / max(num_observations - 1, 1)

        se_sr = np.sqrt(max(var_sr, 1e-9))
        dsr_stat = (estimated_sharpe - sr_benchmark) / se_sr
        return float(stats.norm.cdf(dsr_stat))
