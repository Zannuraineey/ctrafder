"""
Tests for Strategy Tournament & Bayesian Capital Allocation Engine.
"""

import pytest
import numpy as np

from app.tournament.metrics import QuantitativeMetricsCalculator
from app.tournament.allocator import ThompsonSamplingAllocator, StrategyArm
from app.tournament.tournament import StrategyTournamentEngine, TournamentLeaderboardEntry


def test_deflated_sharpe_ratio():
    # Deflated Sharpe should be lower when there are many strategy trials
    sr = 1.8
    dsr_few_trials = QuantitativeMetricsCalculator.calculate_deflated_sharpe(
        estimated_sharpe=sr,
        num_trials=5,
        num_observations=100,
    )
    dsr_many_trials = QuantitativeMetricsCalculator.calculate_deflated_sharpe(
        estimated_sharpe=sr,
        num_trials=100,
        num_observations=100,
    )

    assert 0.0 <= dsr_few_trials <= 1.0
    assert 0.0 <= dsr_many_trials <= 1.0
    # More trials mean higher chance of luck, so DSR must be lower
    assert dsr_many_trials < dsr_few_trials


def test_thompson_sampling_allocator():
    np.random.seed(42)
    allocator = ThompsonSamplingAllocator(min_weight=0.25, max_weight=2.50)
    allocator.register_strategy("WINNING_ALPHA")
    allocator.register_strategy("LOSING_ALPHA")

    # Record 20 winning trades on WINNING_ALPHA
    for _ in range(20):
        allocator.record_outcome("WINNING_ALPHA", pnl=15.0)

    # Record 20 losing trades on LOSING_ALPHA
    for _ in range(20):
        allocator.record_outcome("LOSING_ALPHA", pnl=-10.0)

    weights = allocator.sample_capital_weights(n_samples=500)
    assert "WINNING_ALPHA" in weights
    assert "LOSING_ALPHA" in weights
    assert weights["WINNING_ALPHA"] > weights["LOSING_ALPHA"]
    assert weights["WINNING_ALPHA"] >= 1.2
    assert weights["LOSING_ALPHA"] <= 0.8


def test_strategy_tournament_engine():
    tournament = StrategyTournamentEngine()

    # Simulate some trades
    tournament.record_trade("POC_REACTION", pnl=25.0)
    tournament.record_trade("POC_REACTION", pnl=18.0)
    tournament.record_trade("POC_REACTION", pnl=-5.0)

    tournament.record_trade("TREND_PULLBACK", pnl=-12.0)
    tournament.record_trade("TREND_PULLBACK", pnl=-8.0)

    leaderboard = tournament.run_tournament_ranking()
    assert len(leaderboard) >= 5
    assert leaderboard[0].rank == 1
    assert leaderboard[0].strategy_name == "POC_REACTION"
    assert leaderboard[0].total_pnl > 0
    assert isinstance(leaderboard[0], TournamentLeaderboardEntry)
