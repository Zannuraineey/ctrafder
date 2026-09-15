"""
Unit tests for Feature Pipeline and Technical Indicators.
"""

import pytest
import pandas as pd
import numpy as np
from app.features.technical import (
    calculate_ema,
    calculate_rsi,
    calculate_macd,
    calculate_atr,
    calculate_adx,
    calculate_bollinger_bands,
)
from app.features.feature_pipeline import FeaturePipeline, CANONICAL_FEATURE_COLS
from app.broker.models import Candle
from datetime import datetime, timedelta


def test_technical_indicators_mathematics():
    # Linear price sequence
    prices = pd.Series([float(i) for i in range(1, 101)])

    # EMA test
    ema_10 = calculate_ema(prices, 10)
    assert len(ema_10) == 100
    assert ema_10.iloc[-1] > 90.0

    # RSI test on strictly rising series (should approach 100)
    rsi = calculate_rsi(prices, 14)
    assert rsi.iloc[-1] > 95.0

    # MACD test
    macd, sig, hist = calculate_macd(prices, 12, 26, 9)
    assert len(macd) == 100
    assert hist.iloc[-1] > 0  # In strong uptrend, hist is positive


def test_feature_pipeline_integration():
    candles = []
    base_time = datetime(2026, 1, 1)
    for i in range(60):
        candles.append(
            Candle(
                symbol="TEST",
                timeframe="1m",
                timestamp=base_time + timedelta(minutes=i),
                open=100.0 + i * 0.1,
                high=100.5 + i * 0.1,
                low=99.5 + i * 0.1,
                close=100.2 + i * 0.1,
                volume=100.0,
            )
        )

    vec, df = FeaturePipeline.extract_latest_feature_vector(candles)
    assert len(vec) > 20
    for col in CANONICAL_FEATURE_COLS:
        assert col in vec
        assert isinstance(vec[col], float)
