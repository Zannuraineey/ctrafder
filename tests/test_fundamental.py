"""
Unit tests for Fundamental Engine, Surprise Z-Scores, and News Blackout Shield.
"""

import pytest
from datetime import datetime, timedelta
from app.fundamental.calendar import EconomicCalendar, EconomicEvent, EventImpact
from app.fundamental.surprise_engine import SurpriseEngine
from app.fundamental.blackout import NewsBlackoutShield
from app.broker.models import TradeSide


def test_surprise_engine_z_score():
    # US CPI: Forecast 3.0%, Actual 3.5% -> Surprise is +0.50%
    # With stdev = 0.20, Z = +2.50 (Extremely Hawkish USD)
    event = EconomicEvent(
        id="cpi_01",
        title="US CPI (YoY)",
        currency="USD",
        impact=EventImpact.HIGH,
        timestamp=datetime.utcnow(),
        forecast=3.0,
        actual=3.5,
    )
    z = SurpriseEngine.calculate_surprise_z(event)
    assert z is not None
    assert z >= 2.0

    # High US CPI should be strongly Bearish for Gold (XAUUSD)
    gold_bias = SurpriseEngine.evaluate_symbol_bias("XAUUSD", event)
    assert gold_bias is not None
    assert gold_bias.bias_score < -0.50
    assert gold_bias.recommended_side == TradeSide.SELL

    # High US CPI should be strongly Bullish for USDJPY
    usdjpy_bias = SurpriseEngine.evaluate_symbol_bias("USDJPY", event)
    assert usdjpy_bias is not None
    assert usdjpy_bias.bias_score > 0.50
    assert usdjpy_bias.recommended_side == TradeSide.BUY


def test_news_blackout_shield():
    calendar = EconomicCalendar()
    # Add high-impact USD event 5 minutes from now
    now = datetime.utcnow()
    calendar.events.append(
        EconomicEvent(
            id="fomc_test",
            title="FOMC Statement",
            currency="USD",
            impact=EventImpact.HIGH,
            timestamp=now + timedelta(minutes=5),
            forecast=5.50,
        )
    )
    shield = NewsBlackoutShield(calendar=calendar, pre_event_minutes=15)

    # Gold and EURUSD must be blocked
    xau_blocked, xau_reason = shield.check_blackout("XAUUSD")
    assert xau_blocked is True
    assert "NEWS BLACKOUT" in xau_reason

    eur_blocked, _ = shield.check_blackout("EURUSD")
    assert eur_blocked is True

    # Deriv Synthetic indices must be EXEMPT from news blackouts
    vol_blocked, _ = shield.check_blackout("Vol_15_1s")
    assert vol_blocked is False
