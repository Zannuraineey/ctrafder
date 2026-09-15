"""
Unit tests for Post-Mortem Mistake Learning & Anti-Greed Engine.
"""

from datetime import datetime, timedelta
import pytest

from app.broker.models import TradeRecord, TradeSide, MarketRegime, ExitReason
from app.learning.mistake_engine import MistakeEngine, MistakeType
from app.agents.agent import TradingAgent
from app.market.deriv_universe import AccountTier


def test_revenge_trading_interception():
    """Verify that entering a trade within 180s after a loss triggers a revenge trading veto."""
    engine = MistakeEngine()
    symbol = "XAUUSD"

    # Simulate a losing trade closure
    losing_trade = TradeRecord(
        trade_id="TR_LOSS_001",
        symbol=symbol,
        side=TradeSide.BUY,
        entry_price=2350.0,
        exit_price=2340.0,
        volume_lots=0.05,
        profit_loss=-50.0,
        return_percent=-0.005,
        duration_seconds=45,
        strategy="MOMENTUM",
        risk_amount=50.0,
        risk_percent=0.01,
        balance_before=10000.0,
        balance_after=9950.0,
        entry_timestamp=datetime.utcnow() - timedelta(seconds=50),
        exit_timestamp=datetime.utcnow(),
        exit_reason=ExitReason.STOP_LOSS,
    )
    engine.evaluate_post_trade_outcome(losing_trade, current_balance=9950.0)

    # Immediately attempt another trade on XAUUSD (< 180s)
    eval_res = engine.evaluate_pre_trade_mistake(
        symbol=symbol,
        balance=9950.0,
        risk_percent=0.01,
        regime=MarketRegime.TRENDING_UP,
        whipsaw_prob=0.30,
    )

    assert eval_res.has_mistake
    assert eval_res.mistake_type == MistakeType.REVENGE_TRADING
    assert "Revenge trading prohibited" in eval_res.details


def test_greed_oversizing_interception():
    """Verify that attempting > 2.5% risk on a single trade is intercepted as greed."""
    engine = MistakeEngine()

    eval_res = engine.evaluate_pre_trade_mistake(
        symbol="EURUSD",
        balance=500.0,
        risk_percent=0.06,  # 6% risk attempt (Greed!)
        regime=MarketRegime.TRENDING_UP,
        whipsaw_prob=0.20,
    )

    assert eval_res.has_mistake
    assert eval_res.mistake_type == MistakeType.GREED_OVERSIZING
    assert "exceeds max institutional 2.0% allocation" in eval_res.details


def test_choppy_overtrading_interception():
    """Verify that attempting to trade in choppy/ranging conditions with high whipsaw is intercepted."""
    engine = MistakeEngine()

    eval_res = engine.evaluate_pre_trade_mistake(
        symbol="Vol_50_1s",
        balance=1000.0,
        risk_percent=0.01,
        regime=MarketRegime.CHOPPY,
        whipsaw_prob=0.75,  # 75% whipsaw probability
    )

    assert eval_res.has_mistake
    assert eval_res.mistake_type == MistakeType.CHOPPY_OVERTRADING


def test_agent_penalty_box():
    """Verify agent benching, capital weight slashing, and cooldown logic."""
    agent = TradingAgent(
        agent_id=7,
        name="Test_Quant",
        pod_name="Test Pod",
        specialized_symbols=["EURUSD"],
        base_strategy_name="TREND_PULLBACK",
    )

    assert not agent.is_in_penalty_box()
    assert agent.capital_weight == 1.0

    # Apply penalty for greed
    agent.apply_penalty("Greed sizing detected", minutes=45)

    assert agent.is_in_penalty_box()
    assert agent.capital_weight == 0.50
    assert agent.mistakes_count == 1

    # While benched, agent cannot participate
    assert not agent.is_eligible_for_symbol_and_regime("EURUSD", MarketRegime.TRENDING_UP)


def test_floor_anti_tilt_circuit_breaker():
    """Verify that 2 consecutive losses activate the 15-minute floor cooldown."""
    engine = MistakeEngine()

    # First loss
    t1 = TradeRecord(
        trade_id="TR_1", symbol="EURUSD", side=TradeSide.BUY,
        entry_price=1.08, exit_price=1.079, volume_lots=0.1,
        profit_loss=-10.0, return_percent=-0.001, duration_seconds=30,
        strategy="TREND_PULLBACK", risk_amount=10.0, risk_percent=0.01,
        balance_before=1000.0, balance_after=990.0,
        entry_timestamp=datetime.utcnow(), exit_timestamp=datetime.utcnow(),
        exit_reason=ExitReason.STOP_LOSS,
    )
    engine.evaluate_post_trade_outcome(t1)
    is_tilted, _ = engine.check_floor_tilt_cooldown()
    assert not is_tilted

    # Second consecutive loss
    t2 = TradeRecord(
        trade_id="TR_2", symbol="GBPUSD", side=TradeSide.BUY,
        entry_price=1.28, exit_price=1.279, volume_lots=0.1,
        profit_loss=-10.0, return_percent=-0.001, duration_seconds=30,
        strategy="TREND_PULLBACK", risk_amount=10.0, risk_percent=0.01,
        balance_before=990.0, balance_after=980.0,
        entry_timestamp=datetime.utcnow(), exit_timestamp=datetime.utcnow(),
        exit_reason=ExitReason.STOP_LOSS,
    )
    engine.evaluate_post_trade_outcome(t2)

    is_tilted, reason = engine.check_floor_tilt_cooldown()
    assert is_tilted
    assert "Floor paused" in reason
