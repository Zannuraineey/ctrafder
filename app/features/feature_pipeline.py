"""
Unified Feature Engineering Pipeline.
Transforms raw OHLCV candles into rich feature vectors for ML models and strategy rules.
"""

from typing import List, Dict, Any, Tuple
import pandas as pd
import numpy as np

from app.broker.models import Candle
from app.features.technical import calculate_technical_features
from app.features.price_action import calculate_price_action_features
from app.features.structure import calculate_structure_features
from app.features.volatility import calculate_volatility_features
from app.features.order_flow import calculate_order_flow_features

# Standard canonical feature names used across ML models
CANONICAL_FEATURE_COLS = [
    # Moving Average Distances
    "dist_ema_21",
    "dist_ema_50",
    "dist_ema_200",
    "ema_trend_aligned",
    # Momentum & Oscillator
    "rsi_14",
    "macd_line",
    "macd_signal",
    "macd_hist",
    "adx",
    "plus_di",
    "minus_di",
    "stoch_k",
    "stoch_d",
    # Volatility
    "atr_norm",
    "bb_bandwidth",
    "bb_percent_b",
    "atr_percentile",
    "volatility_expansion_ratio",
    "volatility_regime_code",
    # Price Action
    "body_ratio",
    "upper_wick_ratio",
    "lower_wick_ratio",
    "close_location_value",
    "return_1",
    "return_3",
    "return_5",
    "consecutive_bullish",
    "consecutive_bearish",
    "is_bullish_rejection",
    "is_bearish_rejection",
    "is_engulfing_bullish",
    "is_engulfing_bearish",
    # Structure
    "dist_swing_high",
    "dist_swing_low",
    "bos_bullish",
    "bos_bearish",
    "liquidity_sweep_high",
    "liquidity_sweep_low",
    "structure_trend",
]


class FeaturePipeline:
    """Pipelines candles into a feature matrix."""

    @staticmethod
    def candles_to_dataframe(candles: List[Candle]) -> pd.DataFrame:
        """Convert a list of Candle objects into a pandas DataFrame."""
        if not candles:
            return pd.DataFrame()
        data = [
            {
                "timestamp": c.timestamp,
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
                "volume": c.volume,
            }
            for c in candles
        ]
        df = pd.DataFrame(data)
        df.sort_values("timestamp", inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df

    @classmethod
    def compute_all_features(cls, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute full technical, price action, structural, and volatility features.
        """
        if df.empty or len(df) < 5:
            return df

        res = calculate_technical_features(df)
        res = calculate_price_action_features(res)
        res = calculate_structure_features(res)
        res = calculate_volatility_features(res)
        res = calculate_order_flow_features(res)
        return res

    @classmethod
    def extract_latest_feature_vector(
        cls, candles: List[Candle]
    ) -> Tuple[Dict[str, float], pd.DataFrame]:
        """
        Extract the most recent computed feature row as a dictionary.
        Used for real-time inference.
        """
        df = cls.candles_to_dataframe(candles)
        if len(df) < 30:
            return {}, df

        feat_df = cls.compute_all_features(df)
        latest_row = feat_df.iloc[-1]

        features: Dict[str, float] = {}
        for col in CANONICAL_FEATURE_COLS:
            val = latest_row.get(col, 0.0)
            features[col] = float(val) if pd.notnull(val) and not np.isinf(val) else 0.0

        return features, feat_df
