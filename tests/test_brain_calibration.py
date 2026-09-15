"""
Tests for Quantitative Brain, Probability Calibration, and Uncertainty Estimation.
"""

import pytest
import numpy as np
import pandas as pd

from app.broker.models import TradeSide, MarketRegime
from app.brain.calibration import ProbabilityCalibrator, CalibrationMetrics
from app.brain.uncertainty import UncertaintyEstimator, PredictionInterval
from app.brain.meta_learner import LearnedMetaModel
from app.brain.regime_classifier import StatisticalRegimeClassifier
from app.ai.models.random_forest import RandomForestDirectionModel


def test_probability_calibrator_isotonic_and_platt():
    np.random.seed(42)
    # Generate synthetic uncalibrated probabilities with known true outcomes
    raw_p = np.random.uniform(0.1, 0.9, size=100)
    # True outcome correlated with raw_p
    y_true = (raw_p + np.random.normal(0, 0.15, size=100) > 0.5).astype(int)

    # 1. Isotonic
    iso_cal = ProbabilityCalibrator(method="isotonic")
    iso_cal.fit(raw_p, y_true)
    assert iso_cal.is_fitted
    calibrated_iso = iso_cal.calibrate(raw_p)
    assert len(calibrated_iso) == 100
    assert np.all(calibrated_iso >= 0.01) and np.all(calibrated_iso <= 0.99)

    # 2. Platt Scaling
    platt_cal = ProbabilityCalibrator(method="platt")
    platt_cal.fit(raw_p, y_true)
    assert platt_cal.is_fitted
    calibrated_platt = platt_cal.calibrate(raw_p)
    assert len(calibrated_platt) == 100
    assert np.all(calibrated_platt >= 0.01) and np.all(calibrated_platt <= 0.99)

    # 3. Calibration Evaluation Metrics
    metrics = ProbabilityCalibrator.evaluate_calibration(calibrated_iso, y_true, n_bins=5)
    assert isinstance(metrics, CalibrationMetrics)
    assert 0.0 <= metrics.brier_score <= 1.0
    assert 0.0 <= metrics.expected_calibration_error <= 1.0
    assert len(metrics.reliability_bins) > 0


def test_uncertainty_conformal_bounds():
    np.random.seed(42)
    val_p = np.array([0.65, 0.70, 0.40, 0.80, 0.30, 0.85, 0.20, 0.90, 0.55, 0.75, 0.60, 0.45])
    val_y = np.array([1, 1, 0, 1, 0, 1, 0, 1, 1, 1, 0, 0])

    estimator = UncertaintyEstimator(confidence_level=0.90)
    estimator.calibrate(val_p, val_y)
    assert estimator.is_calibrated
    assert estimator.quantile_threshold > 0.0

    interval = estimator.estimate_uncertainty(
        calibrated_prob=0.72,
        model_probas=[0.70, 0.75, 0.71],
    )
    assert isinstance(interval, PredictionInterval)
    assert interval.point_estimate == 0.72
    assert interval.lower_bound <= interval.point_estimate <= interval.upper_bound
    assert interval.interval_width == round(interval.upper_bound - interval.lower_bound, 4)
    assert interval.epistemic_uncertainty < 0.10  # Low disagreement among models
    assert 0.0 <= interval.aleatoric_uncertainty <= 1.0


def test_learned_meta_learner_prediction():
    rf = RandomForestDirectionModel()
    # Dummy train RF
    df_feat = pd.DataFrame(np.random.randn(40, 5), columns=[f"feat_{i}" for i in range(5)])
    y_series = pd.Series([1 if i % 2 == 0 else 0 for i in range(40)])
    rf.train(df_feat, y_series)

    meta = LearnedMetaModel(base_models=[rf])
    assert meta.is_trained  # Initialized with robust Bayesian prior

    X_row = df_feat.iloc[-1:]
    win_p, quality, score, interval = meta.predict_direction_and_quality(
        X=X_row,
        candidate_side=TradeSide.BUY,
        regime=MarketRegime.TRENDING_UP,
        whipsaw_prob=0.20,
        expected_rr=2.0,
    )

    assert 0.01 <= win_p <= 0.99
    assert 0.01 <= quality <= 0.99
    assert score > 0.0
    assert isinstance(interval, PredictionInterval)
    assert interval.lower_bound <= win_p <= interval.upper_bound


def test_statistical_regime_classifier():
    np.random.seed(42)
    # Synthesize trending OHLCV
    n = 60
    trend = np.linspace(100, 150, n) + np.random.normal(0, 0.5, n)
    high = trend + np.random.uniform(0.2, 1.0, n)
    low = trend - np.random.uniform(0.2, 1.0, n)
    open_p = trend - np.random.normal(0, 0.2, n)
    vol = np.random.uniform(100, 500, n)

    df = pd.DataFrame({"open": open_p, "high": high, "low": low, "close": trend, "volume": vol})
    classifier = StatisticalRegimeClassifier(n_components=3)
    classifier.fit(df)
    assert classifier.is_fitted

    regime, conf = classifier.classify_regime(df)
    assert isinstance(regime, MarketRegime)
    assert 0.0 <= conf <= 1.0
