"""
Tests for Post-Mortem Failure Learning & ML Online Adaptation Engine.
"""
import pytest
from datetime import datetime, timedelta
from app.broker.models import Position, TradeRecord, TradeSide, ExitReason, PositionStatus, SymbolSpecification
from app.learning.post_mortem_engine import PostMortemEngine


@pytest.fixture
def engine():
    return PostMortemEngine()


def test_analyze_active_positions_diagnostics(engine):
    """Verify live position telemetry produces accurate health and stagnation diagnostics."""
    spec = SymbolSpecification(
        symbol="Vol_25_1s", symbol_id=110, description="Vol 25 1s",
        asset_class="SYNTHETIC", digits=4, lot_min=0.2, lot_max=100.0,
        contract_size=1.0, tick_size=0.0001, tick_value=0.0001
    )
    pos = Position(
        id="pos_test01",
        symbol="Vol_25_1s",
        side=TradeSide.BUY,
        volume=2.0,
        entry_price=100.0,
        current_price=103.0,
        stop_loss=101.5,
        take_profit=112.0,
        unrealized_pnl=6.0,
        status=PositionStatus.OPEN,
        opened_at=datetime.utcnow() - timedelta(seconds=45),
        is_be_active=True,
    )
    open_positions = {"pos_test01": pos}
    prices = {"Vol_25_1s": 103.0}
    specs = {"Vol_25_1s": spec}

    diagnostics = engine.analyze_active_positions(open_positions, prices, specs)
    assert len(diagnostics) == 1
    d = diagnostics[0]
    assert d.symbol == "Vol_25_1s"
    assert d.health_status == "TRAILING"
    assert d.stagnation_risk == "LOW"
    assert "PASSED" in d.greed_check
    assert d.duration_seconds >= 44


def test_diagnose_closed_position_and_send_to_ml(engine):
    """Verify that a flat/stagnant trade failure generates a post-mortem and sends fix to ML."""
    trade = TradeRecord(
        trade_id="rec_eur01",
        symbol="EURUSD",
        side=TradeSide.BUY,
        timeframe="1m",
        entry_price=1.08454,
        exit_price=1.08453,
        volume=1000.0,
        volume_lots=0.01,
        stop_loss=1.08350,
        take_profit=1.08700,
        risk_percent=0.01,
        risk_amount=1.04,
        balance_before=1000.0,
        balance_after=999.95,
        profit_loss=-0.05,
        return_percent=-0.005,
        duration_seconds=286,
        strategy="POC_RESPECT_ALIGNMENT",
        exit_reason="TIMEOUT",
        entry_timestamp=datetime.utcnow() - timedelta(seconds=286),
        exit_timestamp=datetime.utcnow(),
    )

    feedback = engine.diagnose_closed_position(trade)
    assert feedback is not None
    assert feedback.symbol == "EURUSD"
    assert "COMMISSION_DRAG" in feedback.failure_mode or "LOW_VOLATILITY" in feedback.failure_mode
    assert "commission" in feedback.root_cause.lower()
    assert "Synthetics" in feedback.ml_adaptation or "weight" in feedback.ml_adaptation
    assert feedback.status == "APPLIED_TO_NEXT_TRADE"

    # Verify that EURUSD is penalized for subsequent trades
    assert engine.is_symbol_permitted("EURUSD") is False
    assert engine.get_symbol_preference_score("EURUSD") < 0.35


def test_positive_reinforcement_boosts_weight(engine):
    """Verify that winning trades reinforce symbol ranking."""
    initial_score = engine.get_symbol_preference_score("Vol_25_1s")
    trade = TradeRecord(
        trade_id="rec_vol01",
        symbol="Vol_25_1s",
        side=TradeSide.BUY,
        timeframe="1m",
        entry_price=100.0,
        exit_price=105.0,
        volume=10.0,
        volume_lots=10.0,
        stop_loss=98.0,
        take_profit=105.0,
        risk_percent=0.02,
        risk_amount=20.0,
        balance_before=1000.0,
        balance_after=1050.0,
        profit_loss=50.0,
        return_percent=5.0,
        duration_seconds=55,
        strategy="POC_BOUNCE",
        exit_reason="TAKE_PROFIT",
        entry_timestamp=datetime.utcnow() - timedelta(seconds=55),
        exit_timestamp=datetime.utcnow(),
    )
    res = engine.diagnose_closed_position(trade)
    assert res is None  # Positive reinforcement doesn't create failure record
    assert engine.get_symbol_preference_score("Vol_25_1s") > initial_score
