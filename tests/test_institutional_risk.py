"""
Unit tests for Institutional Risk: Value-at-Risk (VaR), Volatility Targeting, and Covariance Delta.
"""

import pytest
from app.risk.var import ValueAtRiskEngine
from app.risk.volatility_targeting import VolatilityTargetingEngine
from app.risk.covariance import CovarianceEngine
from app.broker.models import Position, PositionStatus, TradeSide


def test_value_at_risk_engine():
    # 2 positions: 1 lot Gold ($235,000 notional) and 1 lot EURUSD ($100,000 notional)
    positions = [
        Position(
            id="p1",
            symbol="XAUUSD",
            side=TradeSide.BUY,
            volume=100.0,
            entry_price=2350.0,
            current_price=2350.0,
            stop_loss=2340.0,
            take_profit=2360.0,
            status=PositionStatus.OPEN,
        ),
        Position(
            id="p2",
            symbol="EURUSD",
            side=TradeSide.BUY,
            volume=100000.0,
            entry_price=1.0850,
            current_price=1.0850,
            stop_loss=1.0800,
            take_profit=1.0950,
            status=PositionStatus.OPEN,
        ),
    ]

    volatilities = {"XAUUSD": 0.16, "EURUSD": 0.08}
    var_99, cvar_99 = ValueAtRiskEngine.calculate_portfolio_var(positions, volatilities)

    assert var_99 > 0
    assert cvar_99 > var_99  # Expected shortfall is always greater than VaR


def test_volatility_targeting():
    engine = VolatilityTargetingEngine(target_annualized_vol=0.15)

    # In calm market (vol = 0.08), sizing should scale UP
    calm_mult = engine.compute_volatility_multiplier(0.08)
    assert calm_mult > 1.20

    # In extreme shock market (vol = 0.40), sizing should scale DOWN
    turbulent_mult = engine.compute_volatility_multiplier(0.40)
    assert turbulent_mult < 0.60


def test_covariance_currency_delta_veto():
    # Already holding 2 lots of long Gold and 1 lot of long EUR (both are short USD!)
    positions = [
        Position(
            id="p1",
            symbol="XAUUSD",
            side=TradeSide.BUY,
            volume=200.0,  # 2 lots
            entry_price=2350.0,
            current_price=2350.0,
            stop_loss=2340.0,
            take_profit=2360.0,
            status=PositionStatus.OPEN,
        ),
        Position(
            id="p2",
            symbol="EURUSD",
            side=TradeSide.BUY,
            volume=100000.0,  # 1 lot
            entry_price=1.0850,
            current_price=1.0850,
            stop_loss=1.0800,
            take_profit=1.0950,
            status=PositionStatus.OPEN,
        ),
    ]

    # Current net USD exposure is already -3.0 lots
    net_exp = CovarianceEngine.calculate_net_currency_exposure(positions)
    assert net_exp["USD"] <= -3.0

    # Proposing another short USD trade (e.g. BUY 1 lot GBPUSD) must be VETOED by delta cap
    veto_reason = CovarianceEngine.check_currency_delta_cap(
        symbol="GBPUSD",
        side=TradeSide.BUY,
        proposed_lots=1.0,
        open_positions=positions,
        max_net_currency_lots=3.0,
    )
    assert veto_reason is not None
    assert "Net Currency Delta Exceeded" in veto_reason
