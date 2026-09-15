"""
Unit tests for Deep Neural Network Pattern Recognition Model.
"""

import pytest
import pandas as pd
import numpy as np

from app.ai.models.neural_network import NeuralNetworkPatternModel
from app.ai.inference import AIInferenceEngine
from app.broker.models import TradeSignal, TradeSide, SymbolSpecification


def test_neural_network_training_and_inference():
    """Test Neural Network trains with walk-forward validation and predicts probabilities."""
    np.random.seed(42)
    X = pd.DataFrame({
        "rsi": np.random.uniform(20, 80, 60),
        "adx": np.random.uniform(10, 50, 60),
        "momentum_score": np.random.uniform(10, 95, 60),
        "volume_rvol": np.random.uniform(0.5, 3.0, 60),
        "continuation_prob": np.random.uniform(0.3, 0.9, 60),
    })
    # Target: 1 if momentum and continuation are above median
    y = pd.Series(((X["momentum_score"] > 50) & (X["continuation_prob"] > 0.5)).astype(int))

    nn = NeuralNetworkPatternModel(name="test_nn", max_iter=200)
    metrics = nn.train(X, y)

    assert metrics["val_accuracy"] >= 0.0
    assert metrics["val_precision"] >= 0.0
    assert metrics["train_samples"] == 60
    assert nn.is_trained is True

    # Predict probabilities
    probas = nn.predict_proba(X.iloc[:5])
    assert probas.shape == (5, 2)
    assert np.allclose(probas.sum(axis=1), 1.0)

    # Feature importances
    importances = nn.get_feature_importances()
    assert len(importances) == 5
    assert np.isclose(sum(importances.values()), 1.0)


def test_neural_network_in_ai_ensemble():
    """Test AIInferenceEngine integrates Neural Network with Random Forest and Gradient Boosting."""
    engine = AIInferenceEngine()
    model_types = [type(m).__name__ for m in engine.ensemble.models]

    assert "RandomForestDirectionModel" in model_types
    assert "GradientBoostingDirectionModel" in model_types
    assert "NeuralNetworkPatternModel" in model_types
