"""
Tests for Position Protection Engine: Auto-Breakeven, Dynamic Trailing Stop, and Bulk Actions.
"""
import pytest
import asyncio
from datetime import datetime
from app.broker.paper_broker import PaperBroker
from app.broker.models import TradeSide, Tick, ExitReason
from app.config import Settings


@pytest.fixture
def paper_broker():
    settings = Settings(
        trading_mode="paper",
        account_balance=10000.0,
        risk_per_trade=0.01,
        paper_slippage_pips=0.0,
        paper_commission_per_lot=0.04,
    )
    return PaperBroker(settings=settings)


@pytest.mark.asyncio
async def test_auto_breakeven_on_profit(paper_broker):
    """Verify that when a position achieves profit, its SL is automatically moved to breakeven."""
    # Open BUY on Vol_25_1s at 100.00, SL 98.00, TP 110.00
    order = await paper_broker.send_market_order(
        symbol="Vol_25_1s",
        side=TradeSide.BUY,
        volume_lots=2.0,
        stop_loss=98.00,
        take_profit=110.00,
        comment="TEST_POC_BOUNCE",
        current_price=100.00,
    )
    assert len(paper_broker.open_positions) == 1
    pos_id = list(paper_broker.open_positions.keys())[0]
    pos = paper_broker.open_positions[pos_id]
    assert pos.stop_loss == 98.00
    assert not pos.is_be_active

    # Price moves favorably: tick at 102.50 (+$5.00 profit for 2.0 lots)
    tick = Tick(symbol="Vol_25_1s", bid=102.50, ask=102.52, timestamp=datetime.utcnow())
    paper_broker.update_tick(tick)

    # Auto-breakeven should have triggered
    assert pos.is_be_active is True
    assert pos.stop_loss > 98.00
    assert pos.stop_loss >= pos.entry_price  # Stop loss moved to or above entry price
    assert pos.highest_pnl >= 4.0


@pytest.mark.asyncio
async def test_dynamic_trailing_stop(paper_broker):
    """Verify that as profit expands, stop loss trails price to lock in at least 50% of gains."""
    order = await paper_broker.send_market_order(
        symbol="Vol_25_1s",
        side=TradeSide.BUY,
        volume_lots=2.0,
        stop_loss=98.00,
        take_profit=120.00,
        comment="TEST_TRAILING",
        current_price=100.00,
    )
    pos_id = list(paper_broker.open_positions.keys())[0]
    pos = paper_broker.open_positions[pos_id]

    # Large profit expansion: price rallies to 110.00 (+$20 profit)
    tick = Tick(symbol="Vol_25_1s", bid=110.00, ask=110.02, timestamp=datetime.utcnow())
    paper_broker.update_tick(tick)

    assert pos.is_be_active is True
    # Trailing stop should lock in roughly 50% of gain: ~105.00
    assert pos.stop_loss >= 104.00
    assert pos.stop_loss <= 110.00


@pytest.mark.asyncio
async def test_manual_breakeven_and_bulk_actions(paper_broker):
    """Verify manual breakeven and close all methods."""
    # Open 2 positions
    await paper_broker.send_market_order(
        symbol="Vol_25_1s",
        side=TradeSide.BUY,
        volume_lots=1.0,
        stop_loss=95.0,
        take_profit=115.0,
        current_price=100.0,
    )
    await paper_broker.send_market_order(
        symbol="Step_Index",
        side=TradeSide.SELL,
        volume_lots=1.0,
        stop_loss=1260.0,
        take_profit=1220.0,
        current_price=1240.0,
    )
    assert len(paper_broker.open_positions) == 2

    # Bulk Breakeven
    count = await paper_broker.breakeven_all_positions()
    assert count == 2
    for pos in paper_broker.open_positions.values():
        assert pos.is_be_active is True
        if pos.side == TradeSide.BUY:
            assert pos.stop_loss >= pos.entry_price
        else:
            assert pos.stop_loss <= pos.entry_price

    # Bulk Close
    closed_count = await paper_broker.close_all_positions(ExitReason.MANUAL)
    assert closed_count == 2
    assert len(paper_broker.open_positions) == 0
