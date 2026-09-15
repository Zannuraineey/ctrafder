"""
Probability Calibration Engine.
Ensures predicted win probabilities correspond to real empirical frequencies
using Platt Scaling (Sigmoid) and Isotonic Regression.
Computes Brier Score, Expected Calibration Error (ECE), and Maximum Calibration Error (MCE).
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
import numpy as np
import os
import joblib
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss
from loguru import logger


@dataclass
class CalibrationMetrics:
    brier_score: float
    expected_calibration_error: float  # ECE (0.0 to 1.0)
    max_calibration_error: float       # MCE (0.0 to 1.0)
    sample_size: int
    is_well_calibrated: bool           # ECE < 0.08
    reliability_bins: List[Dict[str, float]] = field(default_factory=list)


class ProbabilityCalibrator:
    """
    Calibrates uncalibrated model outputs into true Bayesian posterior probabilities.
    Supports both Platt Scaling (Logistic) and Non-Parametric Isotonic Regression.
    """

    def __init__(self, method: str = "isotonic"):
        self.method = method.lower()
        self.is_fitted = False
        self._calibrator: Optional[Any] = None

    def fit(self, raw_probs: np.ndarray, y_true: np.ndarray) -> "ProbabilityCalibrator":
        """
        Fit calibrator on validation predictions and binary targets (1=Win, 0=Loss).
        """
        p = np.asarray(raw_probs, dtype=np.float64).ravel()
        y = np.asarray(y_true, dtype=np.int32).ravel()

        if len(p) < 10 or len(np.unique(y)) < 2:
            logger.warning("Insufficient samples or single class for calibration. Retaining identity calibrator.")
            self.is_fitted = False
            return self

        p = np.clip(p, 1e-4, 1.0 - 1e-4)

        if self.method == "platt" or self.method == "sigmoid":
            # Platt Scaling: Logistic Regression on log-odds
            log_odds = np.log(p / (1.0 - p)).reshape(-1, 1)
            clf = LogisticRegression(C=1.0, solver="lbfgs")
            clf.fit(log_odds, y)
            self._calibrator = clf
        else:
            # Isotonic Regression: monotonic non-parametric fit
            iso = IsotonicRegression(y_min=0.01, y_max=0.99, out_of_bounds="clip")
            iso.fit(p, y)
            self._calibrator = iso

        self.is_fitted = True
        logger.info(f"Fitted {self.method} probability calibrator on {len(p)} observations.")
        return self

    def calibrate(self, raw_probs: np.ndarray) -> np.ndarray:
        """
        Transform raw probabilities into calibrated probabilities.
        """
        p = np.asarray(raw_probs, dtype=np.float64)
        if not self.is_fitted or self._calibrator is None:
            return np.clip(p, 0.01, 0.99)

        original_shape = p.shape
        p_flat = np.clip(p.ravel(), 1e-4, 1.0 - 1e-4)

        if isinstance(self._calibrator, LogisticRegression):
            log_odds = np.log(p_flat / (1.0 - p_flat)).reshape(-1, 1)
            calibrated = self._calibrator.predict_proba(log_odds)[:, 1]
        else:
            calibrated = self._calibrator.predict(p_flat)

        return np.clip(calibrated.reshape(original_shape), 0.01, 0.99)

    @staticmethod
    def evaluate_calibration(
        probs: np.ndarray,
        y_true: np.ndarray,
        n_bins: int = 10,
    ) -> CalibrationMetrics:
        """
        Compute Brier Score, Expected Calibration Error (ECE), and Reliability Diagram bins.
        """
        p = np.asarray(probs, dtype=np.float64).ravel()
        y = np.asarray(y_true, dtype=np.float64).ravel()
        n = len(p)

        if n == 0 or len(np.unique(y)) < 2:
            return CalibrationMetrics(
                brier_score=0.25,
                expected_calibration_error=0.0,
                max_calibration_error=0.0,
                sample_size=n,
                is_well_calibrated=True,
                reliability_bins=[],
            )

        brier = float(brier_score_loss(y, p))

        bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
        ece = 0.0
        mce = 0.0
        bins_data: List[Dict[str, float]] = []

        for i in range(n_bins):
            bin_lower = bin_edges[i]
            bin_upper = bin_edges[i + 1]
            mask = (p >= bin_lower) & (p < bin_upper if i < n_bins - 1 else p <= bin_upper)
            bin_count = int(np.sum(mask))

            if bin_count > 0:
                avg_confidence = float(np.mean(p[mask]))
                empirical_accuracy = float(np.mean(y[mask]))
                diff = abs(avg_confidence - empirical_accuracy)
                ece += (bin_count / n) * diff
                mce = max(mce, diff)

                bins_data.append({
                    "bin_lower": round(bin_lower, 2),
                    "bin_upper": round(bin_upper, 2),
                    "bin_count": bin_count,
                    "avg_confidence": round(avg_confidence, 4),
                    "empirical_accuracy": round(empirical_accuracy, 4),
                    "calibration_gap": round(diff, 4),
                })

        return CalibrationMetrics(
            brier_score=round(brier, 4),
            expected_calibration_error=round(ece, 4),
            max_calibration_error=round(mce, 4),
            sample_size=n,
            is_well_calibrated=ece < 0.08,
            reliability_bins=bins_data,
        )

    def save(self, filepath: str) -> None:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        joblib.dump(
            {
                "method": self.method,
                "is_fitted": self.is_fitted,
                "calibrator": self._calibrator,
            },
            filepath,
        )

    def load(self, filepath: str) -> None:
        if os.path.exists(filepath):
            data = joblib.load(filepath)
            self.method = data["method"]
            self.is_fitted = data["is_fitted"]
            self._calibrator = data["calibrator"]
