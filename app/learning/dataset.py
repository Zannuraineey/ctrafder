"""
Dataset Construction for ML Training.
Section 45 of project.md.
"""

from typing import Tuple, List
import pandas as pd

from app.broker.models import Candle
from app.features.feature_pipeline import FeaturePipeline, CANONICAL_FEATURE_COLS
from app.learning.labels import compute_double_barrier_labels


class DatasetBuilder:
    """
    Builds clean feature matrices X and label vectors y without data leakage.
    """

    @classmethod
    def build_from_candles(
        cls,
        candles: List[Candle],
        horizon_bars: int = 30,
        rr_ratio: float = 2.0,
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Convert candles to feature matrix X and label vector y.
        """
        df = FeaturePipeline.candles_to_dataframe(candles)
        if len(df) < horizon_bars + 30:
            return pd.DataFrame(), pd.Series()

        # 1. Calculate features
        feat_df = FeaturePipeline.compute_all_features(df)

        # 2. Calculate double-barrier labels
        labels = compute_double_barrier_labels(
            feat_df, horizon_bars=horizon_bars, rr_ratio=rr_ratio
        )

        # 3. Drop rows with incomplete forward horizons
        valid_indices = feat_df.index[:-horizon_bars]
        available_cols = [c for c in CANONICAL_FEATURE_COLS if c in feat_df.columns]

        X = feat_df.loc[valid_indices, available_cols].fillna(0.0)
        y = labels.loc[valid_indices]

        return X, y
