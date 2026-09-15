"""
Unit tests for Paper Broker and trade lifecycle execution.
"""

import pytest
import asyncio
from app.broker.paper_broker import PaperBroker
from app.broker.models import TradeSide, Tick, PositionStatus, ExitReason
from app.database import init_db, DatabaseRepository


@pytest.mark.asyncio
async def test_paper_broker_lifecycle():
    init_db()
    broker = PaperBroker()
    await broker.connect()

    # Initial tick
    broker.update_tick(Tick(symbol="XAUUSD", bid=2350.00, ask=2350.10))

    # Send Market BUY order
    order = await broker.send_market_order(
        symbol="XAUUSD",
        side=TradeSide.BUY,
        volume_lots=0.10,
        stop_loss=2340.00,
        take_profit=2360.00,
        comment="TEST_STRAT",
    )
    assert order.status.value == "FILLED"
    assert len(broker.open_positions) == 1

    pos_id = list(broker.open_positions.keys())[0]
    pos = broker.open_positions[pos_id]
    assert pos.symbol == "XAUUSD"
    assert pos.side == TradeSide.BUY

    # Send tick that triggers TAKE PROFIT (bid >= 2360.00)
    broker.update_tick(Tick(symbol="XAUUSD", bid=2360.50, ask=2360.60))
    await asyncio.sleep(0.05)

    # Position should now be closed
    assert len(broker.open_positions) == 0
    assert len(broker.closed_positions) == 1
    closed_pos = broker.closed_positions[0]
    assert closed_pos.status == PositionStatus.CLOSED
    assert closed_pos.exit_reason == ExitReason.TAKE_PROFIT
    assert closed_pos.realized_pnl > 0

    await broker.disconnect()
