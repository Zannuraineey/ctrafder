"""
Unit tests for dynamic position sizing & lot calculator.
"""

import pytest
from app.broker.models import SymbolSpecification
from app.risk.lot_calculator import LotCalculator


@pytest.fixture
def xauusd_spec():
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


@pytest.fixture
def eurusd_spec():
    return SymbolSpecification(
        symbol="EURUSD",
        digits=5,
        lot_min=0.01,
        lot_max=50.0,
        lot_step=0.01,
        contract_size=100000.0,
        tick_size=0.00001,
        tick_value=1.0,
        margin_rate=0.01,
    )


def test_lot_calculator_normal(xauusd_spec):
    # Balance: $10,000, Risk: 0.5% ($50)
    # Entry: 2350.00, SL: 2345.00 -> 5.00 distance = 500 ticks
    # Cost per lot = 500 * $1.0 = $500/lot
    # Lots = $50 / $500 = 0.10 lots
    lots, risk_amt, margin_req, err = LotCalculator.calculate_lot_size(
        balance=10000.0,
        risk_percent=0.005,
        entry_price=2350.00,
        stop_loss_price=2345.00,
        spec=xauusd_spec,
        free_margin=9000.0,
    )
    assert err is None
    assert lots == 0.10
    assert risk_amt == 50.0
    assert margin_req > 0


def test_lot_calculator_zero_stop_distance(xauusd_spec):
    lots, risk_amt, margin_req, err = LotCalculator.calculate_lot_size(
        balance=10000.0,
        risk_percent=0.005,
        entry_price=2350.00,
        stop_loss_price=2350.00,
        spec=xauusd_spec,
        free_margin=9000.0,
    )
    assert err is not None
    assert lots == 0.0


def test_lot_calculator_insufficient_margin(xauusd_spec):
    lots, risk_amt, margin_req, err = LotCalculator.calculate_lot_size(
        balance=10000.0,
        risk_percent=0.005,
        entry_price=2350.00,
        stop_loss_price=2349.50,
        spec=xauusd_spec,
        free_margin=10.0,  # Only $10 free margin
    )
    assert err is not None
    assert "Insufficient free margin" in err
