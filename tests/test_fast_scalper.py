"""
Unit Tests for Fast Scalper & Order Flow Engine.
Validates tick velocity, DOM order book imbalance, fast EMA 5/9/20 alignment,
and 8-factor Scalp Score computation.
(project.md Sections 1, 2, 4, 6, 7)
"""

from datetime import datetime, timedelta
import pytest
import pandas as pd
import numpy as np

from app.broker.models import Tick, TradeSide, SymbolSpecification
from app.scalping.models import ScalpTier, ScalpScore, DOMQuote
from app.scalping.tick_engine import ScalpTickEngine
from app.scalping.fast_scalper import FastScalper


def test_scalp_tick_engine_velocity_and_dom_imbalance():
    """Test tick engine records velocity dp/dt and Level II DOM imbalance correctly."""
    engine = ScalpTickEngine()
    sym = "Vol_10_1s"
    now = datetime.utcnow()

    # Ingest rising ticks
    t1 = Tick(symbol=sym, bid=100.0, ask=100.05, timestamp=now)
    t2 = Tick(symbol=sym, bid=100.5, ask=100.55, timestamp=now + timedelta(seconds=1))
    t3 = Tick(symbol=sym, bid=101.2, ask=101.25, timestamp=now + timedelta(seconds=2))

    engine.ingest_tick(t1, typical_atr=1.0)
    engine.ingest_tick(t2, typical_atr=1.0)
    metric = engine.ingest_tick(t3, typical_atr=1.0)

    # Positive price velocity expected
    assert metric.velocity_pts_sec > 0.0
    assert metric.spread_points == pytest.approx(0.05, abs=1e-4)

    # DOM quote should show positive buyer pressure
    dom = engine.get_dom_quote(sym)
    assert dom.imbalance_ratio > 0.0
    assert dom.bid_depth > dom.ask_depth


def test_fast_scalper_bullish_impulse_score():
    """Test FastScalper generates high Scalp Score (>= 75) on clean EMA 5/9/20 upward momentum."""
    engine = ScalpTickEngine()
    scalper = FastScalper(engine)
    sym = "Step_Index"

    # Build clean bullish trend candles with expanding volume
    n = 35
    closes = np.linspace(100.0, 115.0, n) + np.random.normal(0, 0.02, n)
    highs = closes + 0.3
    lows = closes - 0.2
    opens = closes - 0.1
    vols = np.linspace(150, 450, n)  # Expanding volume

    df = pd.DataFrame({
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": vols,
    })

    # Ingest favorable rising ticks to reflect real price velocity & DOM imbalance
    now = datetime.utcnow()
    engine.ingest_tick(Tick(symbol=sym, bid=114.0, ask=114.02, timestamp=now), typical_atr=0.5)
    engine.ingest_tick(Tick(symbol=sym, bid=114.6, ask=114.62, timestamp=now + timedelta(seconds=1)), typical_atr=0.5)
    tick_m = engine.ingest_tick(Tick(symbol=sym, bid=115.2, ask=115.22, timestamp=now + timedelta(seconds=2)), typical_atr=0.5)

    score = scalper.evaluate_symbol(sym, df, tick_metric=tick_m)

    assert score.direction == TradeSide.BUY
    assert score.ema_alignment == "BULLISH"
    assert score.total_score >= 75.0
    assert score.tier in (ScalpTier.GOOD, ScalpTier.HIGH_QUALITY)
    assert score.is_eligible is True


def test_fast_scalper_rejects_expensive_spread_or_choppy_market():
    """Test FastScalper rejects candidates with wide spread or flat choppy momentum."""
    engine = ScalpTickEngine()
    scalper = FastScalper(engine)
    sym = "Vol_75"

    # Flat choppy candles
    n = 30
    closes = np.ones(n) * 100.0 + np.sin(np.linspace(0, 10, n)) * 0.05
    highs = closes + 0.1
    lows = closes - 0.1
    opens = closes

    df = pd.DataFrame({
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": [100.0] * n,
    })

    # Excessive spread tick metric
    now = datetime.utcnow()
    tick_m = engine.ingest_tick(
        Tick(symbol=sym, bid=100.0, ask=100.80, timestamp=now),  # Huge 0.80 spread vs 0.20 atr
        typical_atr=0.20,
    )

    score = scalper.evaluate_symbol(sym, df, tick_metric=tick_m)

    # Must not be eligible for trade execution
    assert score.is_eligible is False
    assert score.total_score < 75.0
    assert score.spread_score <= 50.0
