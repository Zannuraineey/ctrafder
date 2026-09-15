"""
Random Forest Classifier Model implementation.
"""

import os
from typing import Dict, Any, List
import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, roc_auc_score
from loguru import logger

from app.ai.models.base import BaseMLModel


class RandomForestDirectionModel(BaseMLModel):
    """
    Random Forest model for trade setup win probability classification.
    """

    def __init__(self, name: str = "random_forest_v1", n_estimators: int = 100):
        super().__init__(name=name)
        self.model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=6,
            min_samples_split=10,
            min_samples_leaf=5,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )

    def train(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, float]:
        self.feature_names = list(X.columns)
        n = len(X)

        # Time-Series Out-of-Sample Validation (project.md Section 5)
        # Never evaluate model metrics on the exact training data it memorized!
        if n >= 30:
            split_idx = int(n * 0.75)
            X_train, X_val = X.iloc[:split_idx], X.iloc[split_idx:]
            y_train, y_val = y.iloc[:split_idx], y.iloc[split_idx:]

            # Train on historical partition
            self.model.fit(X_train, y_train)
            # Evaluate strictly on future unseen out-of-sample data
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

            # Refit on all historical data so the deployed production model retains recent memory
            self.model.fit(X, y)
        else:
            # Fallback for very small datasets
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
            # Return neutral 50/50 probability if untrained
            n_samples = len(X)
            return np.full((n_samples, 2), 0.5)

        # Align features
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
        logger.info(f"Model saved to {file_path}")

    def load(self, file_path: str) -> None:
        data = joblib.load(file_path)
        self.name = data["name"]
        self.version = data["version"]
        self.feature_names = data["feature_names"]
        self.model = data["model"]
        self.is_trained = data["is_trained"]
        logger.info(f"Model {self.name} loaded from {file_path}")

    def get_feature_importances(self) -> Dict[str, float]:
        if not self.is_trained or not hasattr(self.model, "feature_importances_"):
            return {}
        importances = self.model.feature_importances_
        return dict(
            sorted(
                zip(self.feature_names, map(float, importances)),
                key=lambda item: item[1],
                reverse=True,
            )
        )
