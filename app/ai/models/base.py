"""
Base interface for machine learning classification models.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
import pandas as pd
import numpy as np


class BaseMLModel(ABC):
    """Abstract interface for direction/quality ML models."""

    def __init__(self, name: str, version: str = "v1"):
        self.name = name
        self.version = version
        self.feature_names: List[str] = []
        self.is_trained: bool = False

    @abstractmethod
    def train(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, float]:
        """
        Train model and return validation metrics (accuracy, win_rate, etc.).
        """
        pass

    @abstractmethod
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        Return predicted probability array [P(0), P(1)] for binary classification.
        """
        pass

    @abstractmethod
    def save(self, file_path: str) -> None:
        """Save serialized model to file."""
        pass

    @abstractmethod
    def load(self, file_path: str) -> None:
        """Load serialized model from file."""
        pass

    @abstractmethod
    def get_feature_importances(self) -> Dict[str, float]:
        """Return feature importance scores."""
        pass
