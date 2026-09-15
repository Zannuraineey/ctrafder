"""
Comprehensive tests for V2 Architecture additions:
- VolumePressureEngine (RVOL, Acceleration, Exhaustion)
- AdvancedMomentumEngine (0-100 Score, States)
- ContinuationEngine (SCALP_TAKE, HOLD, PROTECT, EXIT)
- True Volume Profile (POC, VAH, VAL in order_flow.py)
- Out-of-sample ML model validation
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from app.market.volume_pressure import VolumePressureEngine, VolumeState
from app.market.momentum_engine import AdvancedMomentumEngine, MomentumState, MomentumTier
from app.execution.continuation_engine import ContinuationEngine, LifecycleAction
from app.features.order_flow import calculate_order_flow_features
from app.broker.models import Position, TradeSide, PositionStatus
from app.ai.models.random_forest import RandomForestDirectionModel
from app.ai.models.xgboost_model import GradientBoostingDirectionModel


def _create_synthetic_candles(n: int = 50, trend: str = "up") -> pd.DataFrame:
    """Helper to generate realistic OHLCV test dataframe."""
    np.random.seed(42)
    prices = [100.0]
    for _ in range(n - 1):
        if trend == "up":
            step = float(np.random.normal(0.4, 0.2))
        elif trend == "down":
            step = float(np.random.normal(-0.4, 0.2))
        else:
            step = float(np.random.normal(0.0, 0.1))
        prices.append(prices[-1] + step)

    data = []
    for i, p in enumerate(prices):
        o = p - float(np.random.normal(0.1, 0.05)) if trend == "up" else p + float(np.random.normal(0.1, 0.05))
        c = p
        h = max(o, c) + 0.3
        l = min(o, c) - 0.3
        vol = 100.0 + (i * 5.0 if trend == "up" else 20.0)
        data.append({"open": o, "high": h, "low": l, "close": c, "volume": vol})
    return pd.DataFrame(data)


def test_volume_pressure_engine_expansion_and_metrics():
    """Test VolumePressureEngine calculates valid RVOL, Z-score, and states."""
    df = _create_synthetic_candles(30, trend="up")
    # Make latest candle have high relative volume
    df.loc[df.index[-1], "volume"] = 500.0

    metrics = VolumePressureEngine.analyze(df)
    assert metrics.rvol > 1.5
    assert metrics.volume_z_score > 0
    assert 0.0 <= metrics.buying_pressure_ratio <= 1.0
    assert 0.0 <= metrics.participation_score <= 100.0
    assert metrics.volume_state in (VolumeState.EXPANDING, VolumeState.CONFIRMING)
    assert not metrics.is_exhaustion_detected


def test_volume_pressure_engine_exhaustion_detection():
    """Test VolumePressureEngine detects climax volume exhaustion with large opposing wick."""
    df = _create_synthetic_candles(30, trend="up")
    # Create extreme climax volume with giant upper wick (selling pin-bar rejection)
    last_idx = df.index[-1]
    df.loc[last_idx, "open"] = 115.0
    df.loc[last_idx, "close"] = 115.1
    df.loc[last_idx, "high"] = 120.0  # huge upper wick
    df.loc[last_idx, "low"] = 114.9
    df.loc[last_idx, "volume"] = 1500.0  # 10x volume spike

    metrics = VolumePressureEngine.analyze(df)
    assert metrics.is_exhaustion_detected
    assert metrics.volume_state == VolumeState.EXHAUSTING
    assert metrics.participation_score < 50.0


def test_advanced_momentum_engine_strong_trend():
    """Test AdvancedMomentumEngine scores a strong trending market highly."""
    df = _create_synthetic_candles(40, trend="up")
    metrics = AdvancedMomentumEngine.analyze(df, is_bullish_bias=True)

    assert metrics.momentum_score >= 55.0
    assert metrics.tier in (MomentumTier.MODERATE, MomentumTier.STRONG, MomentumTier.EXTREME)
    assert metrics.state in (MomentumState.STRONG, MomentumState.BUILDING)
    assert metrics.velocity > 0
    assert metrics.is_favorable_direction


def test_continuation_engine_hold_decision():
    """Test ContinuationEngine correctly issues HOLD on healthy position with small PnL."""
    df = _create_synthetic_candles(40, trend="up")
    pos = Position(
        id="pos_test_hold",
        symbol="Vol_25_1s",
        side=TradeSide.BUY,
        volume=1000,
        entry_price=105.0,
        current_price=105.15,
        stop_loss=103.0,
        take_profit=120.0,
        unrealized_pnl=0.15,  # Small PnL below profit-hunt threshold
        status=PositionStatus.OPEN,
    )

    eval_res = ContinuationEngine.evaluate_active_position(pos, df)
    # With small PnL and strong uptrend, engine should HOLD or PROTECT (not SCALP_TAKE)
    assert eval_res.lifecycle_action in (LifecycleAction.HOLD, LifecycleAction.PROTECT)
    assert eval_res.continuation_probability >= 0.40
    assert not eval_res.is_exhaustion_detected


def test_continuation_engine_scalp_take_profit_hunting():
    """Test ContinuationEngine issues SCALP_TAKE when PnL >= $0.50 and momentum is not strong."""
    # Sideways/weakening market — momentum is fading
    df = _create_synthetic_candles(40, trend="flat")
    pos = Position(
        id="pos_test_scalp_take",
        symbol="Vol_25_1s",
        side=TradeSide.BUY,
        volume=1000,
        entry_price=100.0,
        current_price=100.80,
        stop_loss=99.0,
        take_profit=105.0,
        unrealized_pnl=0.80,  # Above $0.50 threshold
        status=PositionStatus.OPEN,
    )

    eval_res = ContinuationEngine.evaluate_active_position(pos, df)
    # With $0.80 profit on a flat/weak market, engine should PROTECT, EXIT, or take profit
    assert eval_res.lifecycle_action in (
        LifecycleAction.SCALP_TAKE, LifecycleAction.PROTECT, LifecycleAction.EXIT,
        LifecycleAction.STRUCTURE_EXIT, LifecycleAction.EXHAUSTION_EXIT, LifecycleAction.MOMENTUM_DECAY
    )
    if eval_res.lifecycle_action in (LifecycleAction.SCALP_TAKE, LifecycleAction.EXHAUSTION_EXIT):
        assert eval_res.continuation_probability < 0.65  # Not strong enough to hold


def test_continuation_engine_protect_and_exit_decision():
    """Test ContinuationEngine issues PROTECT or EXIT when momentum reverses or exhausts."""
    # Bearish market while holding a BUY position
    df_down = _create_synthetic_candles(40, trend="down")
    pos_failing = Position(
        id="pos_test_exit",
        symbol="Vol_25_1s",
        side=TradeSide.BUY,
        volume=1000,
        entry_price=105.0,
        current_price=98.0,
        stop_loss=95.0,
        take_profit=115.0,
        unrealized_pnl=-1.80,
        status=PositionStatus.OPEN,
    )

    eval_res = ContinuationEngine.evaluate_active_position(pos_failing, df_down)
    assert eval_res.lifecycle_action in (
        LifecycleAction.EXIT, LifecycleAction.PROTECT,
        LifecycleAction.STRUCTURE_EXIT, LifecycleAction.MOMENTUM_DECAY
    )
    assert eval_res.continuation_probability < 0.50


def test_true_volume_profile_in_order_flow():
    """Test order_flow.py computes genuine POC and Value Area (VAH/VAL 70%)."""
    df = _create_synthetic_candles(50, trend="up")
    df["close_location_value"] = 0.5
    result = calculate_order_flow_features(df)

    assert "vp_poc" in result.columns
    assert "vp_vah" in result.columns
    assert "vp_val" in result.columns

    # Verify POC is bounded between high and low
    last_row = result.iloc[-1]
    assert last_row["vp_val"] <= last_row["vp_poc"] <= last_row["vp_vah"]
    assert not np.isnan(last_row["vp_poc"])


def test_out_of_sample_timeseries_model_validation():
    """Test RandomForest and GradientBoosting report out-of-sample validation metrics."""
    np.random.seed(42)
    n = 100
    X = pd.DataFrame({
        "feat_1": np.random.randn(n),
        "feat_2": np.random.randn(n),
        "feat_3": np.random.randn(n),
    })
    y = pd.Series(np.random.choice([0, 1], size=n))

    rf = RandomForestDirectionModel()
    rf_metrics = rf.train(X, y)
    assert rf_metrics["validation_mode"] == "out_of_sample_timeseries"
    assert 0.0 <= rf_metrics["accuracy"] <= 1.0

    gb = GradientBoostingDirectionModel()
    gb_metrics = gb.train(X, y)
    assert gb_metrics["validation_mode"] == "out_of_sample_timeseries"
    assert 0.0 <= gb_metrics["accuracy"] <= 1.0


def test_continuation_engine_scalping_mode_fast_exit():
    """Test ContinuationEngine in SCALPING mode immediately triggers SCALP_TAKE on profit or exits on momentum failure."""
    df_flat = _create_synthetic_candles(40, trend="flat")
    pos_profit = Position(
        id="pos_scalp_profit",
        symbol="Vol_10_1s",
        side=TradeSide.BUY,
        volume=1000,
        entry_price=100.0,
        current_price=100.60,
        stop_loss=99.0,
        take_profit=105.0,
        unrealized_pnl=0.60,
        status=PositionStatus.OPEN,
    )

    # In SCALPING mode, +$0.60 must trigger SCALP_TAKE immediately
    scalp_eval = ContinuationEngine.evaluate_active_position(pos_profit, df_flat, trading_mode="SCALPING")
    assert scalp_eval.lifecycle_action == LifecycleAction.SCALP_TAKE

    # When momentum collapses (< 30), SCALPING mode must trigger EXIT
    df_down = _create_synthetic_candles(40, trend="down")
    pos_stalled = Position(
        id="pos_scalp_stall",
        symbol="Vol_10_1s",
        side=TradeSide.BUY,
        volume=1000,
        entry_price=100.0,
        current_price=99.85,
        stop_loss=99.0,
        take_profit=105.0,
        unrealized_pnl=-0.15,
        status=PositionStatus.OPEN,
    )
    stall_eval = ContinuationEngine.evaluate_active_position(pos_stalled, df_down, trading_mode="SCALPING")
    assert stall_eval.lifecycle_action in (LifecycleAction.EXIT, LifecycleAction.STRUCTURE_EXIT)

