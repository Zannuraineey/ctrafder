"""
Model Training Pipeline.
Trains and validates ML models using double-barrier datasets.
Section 48 and 78 of project.md.
"""

from typing import Dict, Any, List, Optional
import pandas as pd
from sklearn.model_selection import train_test_split
from loguru import logger

from app.broker.models import Candle
from app.learning.dataset import DatasetBuilder
from app.learning.model_registry import ModelRegistry
from app.ai.models.random_forest import RandomForestDirectionModel
from app.ai.models.xgboost_model import GradientBoostingDirectionModel


class ModelTrainer:
    """
    Automated training and out-of-sample validation pipeline.
    """

    @classmethod
    def train_models_on_candles(
        cls,
        candles: List[Candle],
        test_size: float = 0.25,
    ) -> Dict[str, Any]:
        """
        Train both Random Forest and Gradient Boosting models, validating out-of-sample.
        """
        logger.info(f"Building training dataset from {len(candles)} candles...")
        X, y = DatasetBuilder.build_from_candles(candles)

        if len(X) < 40 or len(y.unique()) < 2:
            logger.warning("Insufficient data or single class in dataset for training.")
            return {"status": "insufficient_data"}

        # Time-series split (no lookahead shuffle)
        split_idx = int(len(X) * (1.0 - test_size))
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

        results = {}

        # 1. Train Random Forest
        rf = RandomForestDirectionModel(name="rf_direction")
        rf_metrics = rf.train(X_train, y_train)

        # Validate on out-of-sample test set
        test_proba = rf.predict_proba(X_test)[:, 1]
        test_preds = (test_proba >= 0.5).astype(int)
        test_acc = float((test_preds == y_test).mean())
        rf_metrics["test_accuracy"] = round(test_acc, 4)

        ModelRegistry.save_model(rf, stage="production", metrics=rf_metrics)
        results["random_forest"] = rf_metrics

        # 2. Train Gradient Boosting
        gb = GradientBoostingDirectionModel(name="gb_direction")
        gb_metrics = gb.train(X_train, y_train)

        gb_test_proba = gb.predict_proba(X_test)[:, 1]
        gb_test_preds = (gb_test_proba >= 0.5).astype(int)
        gb_metrics["test_accuracy"] = round(float((gb_test_preds == y_test).mean()), 4)

        ModelRegistry.save_model(gb, stage="production", metrics=gb_metrics)
        results["gradient_boosting"] = gb_metrics

        return results
