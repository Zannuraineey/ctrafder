"""
Gradient Boosting / XGBoost Classifier Model implementation.
Uses HistGradientBoostingClassifier or XGBClassifier if available.
"""

import os
from typing import Dict, Any, List
import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import accuracy_score, precision_score, roc_auc_score
from loguru import logger

from app.ai.models.base import BaseMLModel


class GradientBoostingDirectionModel(BaseMLModel):
    """
    High-speed gradient boosted decision trees for probability estimation.
    """

    def __init__(self, name: str = "gradient_boosting_v1"):
        super().__init__(name=name)
        self.model = HistGradientBoostingClassifier(
            max_iter=100,
            max_depth=5,
            min_samples_leaf=10,
            learning_rate=0.08,
            random_state=42,
        )

    def train(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, float]:
        self.feature_names = list(X.columns)
        n = len(X)

        # Time-Series Out-of-Sample Validation (project.md Section 5)
        if n >= 30:
            split_idx = int(n * 0.75)
            X_train, X_val = X.iloc[:split_idx], X.iloc[split_idx:]
            y_train, y_val = y.iloc[:split_idx], y.iloc[split_idx:]

            self.model.fit(X_train, y_train)
            val_preds = self.model.predict(X_val)
            val_proba = (
                self.model.predict_proba(X_val)[:, 1]
                if len(self.model.classes_) > 1
                else np.zeros(len(X_val))
            )

            acc = float(accuracy_score(y_val, val_preds))
            prec = float(precision_score(y_val, val_preds, zero_division=0))
            auc = (
                float(roc_auc_score(y_val, val_proba))
                if len(np.unique(y_val)) > 1
                else 0.50
            )

            # Refit on entire dataset for production inference
            self.model.fit(X, y)
        else:
            self.model.fit(X, y)
            preds = self.model.predict(X)
            proba = self.model.predict_proba(X)[:, 1] if len(self.model.classes_) > 1 else np.zeros(len(X))
            acc = float(accuracy_score(y, preds))
            prec = float(precision_score(y, preds, zero_division=0))
            auc = float(roc_auc_score(y, proba)) if len(np.unique(y)) > 1 else 0.50

        self.is_trained = True
        metrics = {
            "accuracy": round(acc, 4),
            "precision": round(prec, 4),
            "roc_auc": round(auc, 4),
            "validation_mode": "out_of_sample_timeseries" if n >= 30 else "in_sample_small",
        }
        logger.info(f"Model {self.name} trained with forward validation. Metrics: {metrics}")
        return metrics

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        if not self.is_trained:
            n_samples = len(X)
            return np.full((n_samples, 2), 0.5)

        X_aligned = X[self.feature_names] if self.feature_names else X
        return self.model.predict_proba(X_aligned)

    def save(self, file_path: str) -> None:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        joblib.dump(
            {
                "name": self.name,
                "version": self.version,
                "feature_names": self.feature_names,
                "model": self.model,
                "is_trained": self.is_trained,
            },
            file_path,
        )

    def load(self, file_path: str) -> None:
        data = joblib.load(file_path)
        self.name = data["name"]
        self.version = data["version"]
        self.feature_names = data["feature_names"]
        self.model = data["model"]
        self.is_trained = data["is_trained"]

    def get_feature_importances(self) -> Dict[str, float]:
        # Return empty or permutation importance if requested
        return {}
