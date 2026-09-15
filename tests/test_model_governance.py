"""
Tests for Model Governance, Covariate Drift Detection, and Circuit Breakers.
"""

import pytest
import numpy as np
from app.brain.governance import ModelGovernanceRegistry, ModelVersionRecord, DriftReport


def test_model_version_registration_and_hash():
    reg = ModelGovernanceRegistry()
    mock_weights = b"random_forest_v1_weights_dummy_bytes_12345"
    
    rec = reg.register_production_model(
        model_name="rf_direction",
        model_bytes=mock_weights,
        val_accuracy=0.62,
        val_roc_auc=0.68,
        val_brier_score=0.21,
    )

    assert isinstance(rec, ModelVersionRecord)
    assert rec.status == "PRODUCTION"
    assert rec.is_active is True
    assert len(rec.model_hash) == 16
    assert reg.active_version == rec

    # Registering a new version deactivates the old one
    new_weights = b"rf_direction_v2_updated_weights"
    rec2 = reg.register_production_model(
        model_name="rf_direction",
        model_bytes=new_weights,
        val_accuracy=0.65,
        val_roc_auc=0.71,
        val_brier_score=0.19,
    )
    assert rec2.is_active is True
    assert rec.is_active is False
    assert rec.status == "DEPRECATED"
    assert reg.active_version == rec2


def test_ks_drift_detection_normal_vs_drifted():
    reg = ModelGovernanceRegistry(drift_alpha=0.05)
    np.random.seed(42)

    # Establish baseline reference feature distributions (e.g. standard normal)
    ref_f1 = np.random.normal(0.0, 1.0, 100)
    ref_f2 = np.random.normal(10.0, 2.0, 100)
    reg.register_production_model(
        model_name="ensemble",
        model_bytes=b"ensemble_bytes",
        val_accuracy=0.60,
        val_roc_auc=0.65,
        val_brier_score=0.22,
        reference_data={"feature_1": ref_f1, "feature_2": ref_f2},
    )

    # 1. Feed statistically identical live features (no drift)
    for _ in range(50):
        reg.record_live_features({
            "feature_1": float(np.random.normal(0.0, 1.0)),
            "feature_2": float(np.random.normal(10.0, 2.0)),
        })

    report = reg.check_covariate_drift()
    assert isinstance(report, DriftReport)
    assert report.is_drift_detected is False
    assert report.alert_level == "NORMAL"

    # 2. Feed heavily shifted live features (severe distribution drift)
    for _ in range(50):
        reg.record_live_features({
            "feature_1": float(np.random.normal(5.0, 1.0)),  # mean shifted from 0 -> 5
            "feature_2": float(np.random.normal(25.0, 2.0)), # mean shifted from 10 -> 25
        })

    drift_report = reg.check_covariate_drift()
    assert drift_report.is_drift_detected is True
    assert "feature_1" in drift_report.drifted_features
    assert "feature_2" in drift_report.drifted_features
    assert drift_report.alert_level == "CRITICAL"


def test_performance_circuit_breaker():
    reg = ModelGovernanceRegistry()
    reg.register_production_model(
        model_name="gb_scalper",
        model_bytes=b"gb_bytes",
        val_accuracy=0.61,
        val_roc_auc=0.66,
        val_brier_score=0.20,
    )

    # Not enough trades (< 10) -> circuit breaker should not trip
    tripped = reg.evaluate_circuit_breaker(recent_win_rate=0.20, recent_brier_score=0.35, n_trades=5)
    assert tripped is False
    assert reg.is_circuit_breaker_tripped is False

    # Healthy performance -> remains active
    tripped = reg.evaluate_circuit_breaker(recent_win_rate=0.55, recent_brier_score=0.21, n_trades=20)
    assert tripped is False
    assert reg.is_circuit_breaker_tripped is False
    assert reg.active_version.is_active is True

    # Severe degradation (win rate falls below 35% or Brier > 0.30) -> trips circuit breaker
    tripped = reg.evaluate_circuit_breaker(recent_win_rate=0.25, recent_brier_score=0.32, n_trades=20)
    assert tripped is True
    assert reg.is_circuit_breaker_tripped is True
    assert reg.active_version.status == "ROLLED_BACK"
    assert reg.active_version.is_active is False
