"""
Tests for Two-Way State Reconciliation and Execution Analytics Engine.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock

from app.broker.models import Position, PositionStatus, TradeSide, ExitReason, SymbolSpecification
from app.execution.reconciliation import InstitutionalReconciliationWorker, ReconciliationReport
from app.execution.analytics import ExecutionAnalyticsEngine, ExecutionQualitySummary


@pytest.mark.asyncio
async def test_reconciliation_detects_orphan_and_external():
    now = datetime.utcnow()
    pos_local_1 = Position(
        id="pos_1",
        symbol="Step_Index",
        side=TradeSide.BUY,
        volume=10.0,
        entry_price=1240.0,
        current_price=1242.0,
        stop_loss=1235.0,
        take_profit=1250.0,
        unrealized_pnl=2.0,
        status=PositionStatus.OPEN,
        opened_at=now - timedelta(minutes=5),
    )
    pos_local_orphan = Position(
        id="pos_orphan",
        symbol="Vol_25_1s",
        side=TradeSide.SELL,
        volume=50.0,
        entry_price=380.0,
        current_price=382.0,
        stop_loss=385.0,
        take_profit=370.0,
        unrealized_pnl=-1.0,
        status=PositionStatus.OPEN,
        opened_at=now - timedelta(minutes=10),
    )
    pos_broker_external = Position(
        id="pos_external",
        symbol="Crash_500",
        side=TradeSide.BUY,
        volume=20.0,
        entry_price=1250.0,
        current_price=1251.0,
        stop_loss=1240.0,
        take_profit=1270.0,
        unrealized_pnl=1.0,
        status=PositionStatus.OPEN,
        opened_at=now - timedelta(minutes=2),
    )

    mock_broker = AsyncMock()
    # Broker only has pos_1 and pos_external (pos_orphan was closed on broker server)
    mock_broker.get_open_positions.return_value = [pos_local_1, pos_broker_external]

    worker = InstitutionalReconciliationWorker(mock_broker)
    local_positions = [pos_local_1, pos_local_orphan]

    reconciled, report = await worker.reconcile(local_positions, auto_heal=True)

    assert isinstance(report, ReconciliationReport)
    assert not report.is_synchronized
    assert "pos_orphan" in report.missing_in_broker
    assert "pos_external" in report.unmapped_in_broker
    assert pos_local_orphan.status == PositionStatus.CLOSED
    assert len(reconciled) == 2
    assert any(p.id == "pos_external" for p in reconciled)


def test_execution_analytics_slippage_and_summary():
    engine = ExecutionAnalyticsEngine()
    spec = SymbolSpecification(
        symbol="EURUSD",
        digits=5,
        tick_size=0.00001,
        contract_size=100000.0,
    )

    t_signal = datetime.utcnow()
    t_fill = t_signal + timedelta(milliseconds=45)

    # 1. Fill with 0.5 pip adverse slippage on Buy
    fill1 = engine.record_fill(
        trade_id="t1",
        symbol="EURUSD",
        side=TradeSide.BUY,
        requested_price=1.08500,
        executed_price=1.08505,
        spec=spec,
        lots=0.1,
        signal_timestamp=t_signal,
        fill_timestamp=t_fill,
        current_spread=0.00012,
    )

    assert fill1.latency_ms >= 40.0
    assert fill1.slippage_pips == 0.5
    assert fill1.slippage_dollar > 0.0  # Adverse dollar cost

    # 2. Fill with 0.2 pip price improvement on Sell
    fill2 = engine.record_fill(
        trade_id="t2",
        symbol="EURUSD",
        side=TradeSide.SELL,
        requested_price=1.08500,
        executed_price=1.08502,
        spec=spec,
        lots=0.1,
        signal_timestamp=t_signal,
        fill_timestamp=t_signal + timedelta(milliseconds=80),
        current_spread=0.00010,
    )
    assert fill2.slippage_pips == -0.2

    # Summary
    summary = engine.get_quality_summary("EURUSD")
    assert isinstance(summary, ExecutionQualitySummary)
    assert summary.total_fills == 2
    assert summary.p50_latency_ms > 0
