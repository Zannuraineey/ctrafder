"""
Unit tests for Strategy Engine and Router.
"""

import pytest
import pandas as pd
import numpy as np
from app.broker.models import MarketRegime, SymbolSpecification, TradeSide
from app.strategies.trend_pullback import TrendPullbackStrategy
from app.strategies.mean_reversion import MeanReversionStrategy
from app.strategies.router import StrategyRouter


@pytest.fixture
def spec():
    return SymbolSpecification(
        symbol="XAUUSD",
        digits=2,
        lot_min=0.01,
        lot_max=20.0,
        lot_step=0.01,
        contract_size=100.0,
        tick_size=0.01,
        tick_value=1.0,
    )


def test_mean_reversion_blocks_in_strong_trend(spec):
    strat = MeanReversionStrategy()
    # High ADX (35) indicates strong trend
    df = pd.DataFrame(
        {
            "close": [100.0] * 35,
            "open": [99.5] * 35,
            "high": [101.0] * 35,
            "low": [99.0] * 35,
            "adx": [35.0] * 35,
            "rsi_14": [25.0] * 35,
            "bb_percent_b": [0.02] * 35,
            "bb_middle": [105.0] * 35,
            "atr_14": [1.0] * 35,
            "is_bullish_rejection": [1] * 35,
        }
    )
    # Even if regime is RANGING, elevated ADX must block mean reversion to prevent counter-trend stopouts
    sig = strat.evaluate("XAUUSD", df, MarketRegime.RANGING, spec)
    assert sig is None


def test_strategy_router_dispatches_correct_strategies(spec):
    router = StrategyRouter()
    # In TRENDING_UP regime, TrendPullback and Momentum are eligible
    df = pd.DataFrame(
        {
            "close": [100.0] * 35,
            "open": [99.5] * 35,
            "high": [101.0] * 35,
            "low": [99.0] * 35,
            "ema_21": [99.0] * 35,
            "ema_50": [98.0] * 35,
            "ema_200": [90.0] * 35,
            "adx": [28.0] * 35,
            "plus_di": [30.0] * 35,
            "minus_di": [10.0] * 35,
            "atr_14": [1.0] * 35,
            "ema_trend_aligned": [1] * 35,
            "return_3": [0.01] * 35,
            "close_location_value": [0.6] * 35,
            "body_ratio": [0.6] * 35,
            "swing_low_level": [95.0] * 35,
            "swing_high_level": [105.0] * 35,
            "is_bullish_rejection": [0] * 35,
            "is_engulfing_bullish": [0] * 35,
        }
    )
    candidates = router.route_and_evaluate("XAUUSD", df, MarketRegime.TRENDING_UP, spec)
    # Should evaluate and return at least 1 momentum candidate
    assert len(candidates) >= 1
    assert candidates[0].side == TradeSide.BUY
