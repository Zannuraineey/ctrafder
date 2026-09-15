"""
Unit tests for deterministic Risk Engine.
Verifies that Risk Engine vetoes trades whenever any safety rule fails.
Section 28 and 102 of project.md.
"""

import pytest
from datetime import datetime

from app.broker.models import (
    TradeSignal,
    TradeSide,
    AIDecisionObject,
    AccountInfo,
    SymbolSpecification,
    Position,
    PositionStatus,
    Tick,
    MarketRegime,
)
from app.risk.manager import RiskEngine
from app.config.settings import Settings


@pytest.fixture
def risk_engine():
    settings = Settings(
        max_daily_loss=0.02,
        risk_per_trade=0.005,
        max_drawdown=0.10,
        max_open_positions=3,
        min_direction_probability=0.75,
        min_trade_quality=0.70,
        max_whipsaw_probability=0.25,
        min_risk_reward=1.5,
        max_spread_pips=3.0,
    )
    return RiskEngine(settings=settings)


@pytest.fixture
def default_account():
    return AccountInfo(
        account_id="TEST",
        broker="TestBroker",
        balance=10000.0,
        equity=10000.0,
        daily_pnl=0.0,
        free_margin=9000.0,
    )


@pytest.fixture
def xau_spec():
    return SymbolSpecification(
        symbol="XAUUSD",
        digits=2,
        lot_min=0.01,
        lot_max=20.0,
        lot_step=0.01,
        contract_size=100.0,
        tick_size=0.01,
        tick_value=1.0,
        margin_rate=0.01,
    )


def test_risk_approves_valid_trade(risk_engine, default_account, xau_spec):
    signal = TradeSignal(
        symbol="XAUUSD",
        side=TradeSide.BUY,
        strategy="TREND_PULLBACK",
        timeframe="1m",
        entry_price=2350.00,
        stop_loss=2345.00,
        take_profit=2360.00,  # 2:1 R:R
    )
    ai_dec = AIDecisionObject(
        symbol="XAUUSD",
        direction=TradeSide.BUY,
        buy_probability=0.85,
        trade_quality=0.88,
        whipsaw_probability=0.10,
        expected_rr=2.0,
    )
    tick = Tick(symbol="XAUUSD", bid=2349.99, ask=2350.01)

    decision = risk_engine.evaluate_trade(
        signal=signal,
        ai_decision=ai_dec,
        account=default_account,
        spec=xau_spec,
        current_tick=tick,
        open_positions=[],
    )
    assert decision.approved is True
    assert decision.volume_lots > 0
    assert decision.veto_reason is None


def test_risk_vetoes_daily_loss_exceeded(risk_engine, default_account, xau_spec):
    # Max daily loss is 2% = $200. Set daily PnL to -$250
    default_account.daily_pnl = -250.0

    signal = TradeSignal(
        symbol="XAUUSD",
        side=TradeSide.BUY,
        strategy="TREND_PULLBACK",
        timeframe="1m",
        entry_price=2350.00,
        stop_loss=2345.00,
        take_profit=2360.00,
    )
    ai_dec = AIDecisionObject(
        symbol="XAUUSD",
        direction=TradeSide.BUY,
        buy_probability=0.90,
        trade_quality=0.90,
        whipsaw_probability=0.05,
        expected_rr=2.0,
    )
    tick = Tick(symbol="XAUUSD", bid=2349.99, ask=2350.01)

    decision = risk_engine.evaluate_trade(
        signal=signal,
        ai_decision=ai_dec,
        account=default_account,
        spec=xau_spec,
        current_tick=tick,
        open_positions=[],
    )
    assert decision.approved is False
    assert "Daily loss limit exceeded" in decision.veto_reason


def test_risk_vetoes_high_whipsaw(risk_engine, default_account, xau_spec):
    signal = TradeSignal(
        symbol="XAUUSD",
        side=TradeSide.BUY,
        strategy="TREND_PULLBACK",
        timeframe="1m",
        entry_price=2350.00,
        stop_loss=2345.00,
        take_profit=2360.00,
    )
    # Whipsaw 40% exceeds 25% max limit
    ai_dec = AIDecisionObject(
        symbol="XAUUSD",
        direction=TradeSide.BUY,
        buy_probability=0.85,
        trade_quality=0.75,
        whipsaw_probability=0.40,
        expected_rr=2.0,
    )
    tick = Tick(symbol="XAUUSD", bid=2349.99, ask=2350.01)

    decision = risk_engine.evaluate_trade(
        signal=signal,
        ai_decision=ai_dec,
        account=default_account,
        spec=xau_spec,
        current_tick=tick,
        open_positions=[],
    )
    assert decision.approved is False
    assert "Whipsaw probability" in decision.veto_reason


def test_risk_vetoes_duplicate_symbol(risk_engine, default_account, xau_spec):
    signal = TradeSignal(
        symbol="XAUUSD",
        side=TradeSide.BUY,
        strategy="TREND_PULLBACK",
        timeframe="1m",
        entry_price=2350.00,
        stop_loss=2345.00,
        take_profit=2360.00,
    )
    ai_dec = AIDecisionObject(
        symbol="XAUUSD",
        direction=TradeSide.BUY,
        buy_probability=0.85,
        trade_quality=0.88,
        whipsaw_probability=0.10,
        expected_rr=2.0,
    )
    tick = Tick(symbol="XAUUSD", bid=2349.99, ask=2350.01)

    # Active position on XAUUSD already exists
    active_pos = Position(
        id="pos_1",
        symbol="XAUUSD",
        side=TradeSide.BUY,
        volume=10.0,
        entry_price=2348.0,
        current_price=2350.0,
        stop_loss=2340.0,
        take_profit=2360.0,
        status=PositionStatus.OPEN,
    )

    decision = risk_engine.evaluate_trade(
        signal=signal,
        ai_decision=ai_dec,
        account=default_account,
        spec=xau_spec,
        current_tick=tick,
        open_positions=[active_pos],
    )
    assert decision.approved is False
    assert "Duplicate position active" in decision.veto_reason
