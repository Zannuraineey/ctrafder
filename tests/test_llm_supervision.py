"""
Tests for Institutional LLM Supervisory Agent and Schema Enforcement.
"""

import pytest
from datetime import datetime, timezone

from app.supervision.schemas import (
    MacroSupervisoryDirective,
    PostMortemAttributionReport,
    DeskExecutiveBriefing,
)
from app.supervision.supervisor import LLMSupervisor
from app.broker.models import TradeRecord, TradeSide, ExitReason


def test_macro_directive_schema_validation():
    # Valid directive
    directive = MacroSupervisoryDirective(
        directive_id="DIR_TEST_001",
        timestamp=datetime.now(timezone.utc),
        regime_assessment="VOLATILITY_EXPANSION",
        risk_multiplier_cap=0.8,
        forbidden_symbols=["Crash_500"],
        recommended_focus_symbols=["Vol_25_1s"],
        macro_rationale="Realized volatility exceeds 95th percentile threshold.",
        confidence=0.9,
    )
    assert directive.risk_multiplier_cap == 0.8
    assert "Crash_500" in directive.forbidden_symbols

    # Clamp risk cap if out of bounds
    directive_high = MacroSupervisoryDirective(
        directive_id="DIR_TEST_002",
        timestamp=datetime.now(timezone.utc),
        regime_assessment="CALM_TRENDING",
        risk_multiplier_cap=2.5,  # Above max 1.5
        macro_rationale="Extremely stable macro environment.",
    )
    assert directive_high.risk_multiplier_cap == 1.5


def test_supervisor_evaluate_macro_regime_volatility():
    sup = LLMSupervisor()

    # High volatility trigger
    high_vol_dir = sup.evaluate_macro_regime(
        market_stats={},
        recent_volatility=0.045,  # > 0.035
    )
    assert high_vol_dir.regime_assessment == "VOLATILITY_EXPANSION"
    assert high_vol_dir.risk_multiplier_cap <= 0.70
    assert "Crash_500" in high_vol_dir.forbidden_symbols

    # Normal calm trigger
    normal_dir = sup.evaluate_macro_regime(
        market_stats={},
        recent_volatility=0.02,
    )
    assert normal_dir.regime_assessment == "CALM_TRENDING"
    assert normal_dir.risk_multiplier_cap >= 1.0


def test_supervisor_trade_attribution_slippage_vs_variance():
    sup = LLMSupervisor()

    # Winning trade
    win_trade = TradeRecord(
        trade_id="TR_001",
        symbol="Vol_25_1s",
        side=TradeSide.BUY,
        entry_price=100.0,
        exit_price=105.0,
        volume_lots=0.1,
        balance_before=10000.0,
        balance_after=10050.0,
        profit_loss=50.0,
        return_percent=0.5,
        duration_seconds=60,
        strategy="poc_momentum",
        entry_timestamp=datetime.now(timezone.utc),
        exit_timestamp=datetime.now(timezone.utc),
        exit_reason="TAKE_PROFIT",
    )
    win_report = sup.audit_trade_attribution(win_trade, slippage_pips=0.2, latency_ms=45.0)
    assert win_report.pnl == 50.0
    assert win_report.execution_drag_identified is False

    # Loss trade with high slippage
    loss_trade = TradeRecord(
        trade_id="TR_002",
        symbol="Step_Index",
        side=TradeSide.SELL,
        entry_price=200.0,
        exit_price=205.0,
        volume_lots=0.1,
        balance_before=10000.0,
        balance_after=9955.0,
        profit_loss=-45.0,
        return_percent=-0.45,
        duration_seconds=45,
        strategy="fast_scalper",
        entry_timestamp=datetime.now(timezone.utc),
        exit_timestamp=datetime.now(timezone.utc),
        exit_reason="STOP_LOSS",
    )
    loss_report = sup.audit_trade_attribution(loss_trade, slippage_pips=2.4, latency_ms=520.0)
    assert loss_report.root_cause_category == "SLIPPAGE_OR_LATENCY_DRAG"
    assert loss_report.execution_drag_identified is True


def test_supervisor_desk_briefing():
    sup = LLMSupervisor()
    briefing = sup.generate_desk_briefing(
        equity=10250.0,
        drawdown_pct=0.02,
        tournament_summary={"top_strategy": "poc_momentum", "allocation_weights": {"poc_momentum": 1.25}},
        is_circuit_breaker_active=False,
    )
    assert isinstance(briefing, DeskExecutiveBriefing)
    assert briefing.overall_posture == "AGGRESSIVE_ALPHA"
    assert briefing.active_circuit_breaker is False
    assert "poc_momentum" in briefing.top_performing_strategy
