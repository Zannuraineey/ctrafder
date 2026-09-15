"""
Uncertainty Estimation Engine.
Computes non-parametric Conformal Prediction intervals,
epistemic uncertainty (ensemble model disagreement), and
aleatoric uncertainty (market outcome entropy).
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import numpy as np
import os
import joblib
from loguru import logger


@dataclass
class PredictionInterval:
    point_estimate: float            # Point estimate (calibrated win probability)
    lower_bound: float               # Lower bound of (1 - alpha) conformal interval
    upper_bound: float               # Upper bound of (1 - alpha) conformal interval
    interval_width: float            # Uncertainty span (upper - lower)
    epistemic_uncertainty: float     # Model disagreement across ensemble
    aleatoric_uncertainty: float     # Shannon entropy of probability distribution
    confidence_level: float          # e.g., 0.90 (90% coverage guarantee)
    is_high_uncertainty: bool        # True if interval_width > 0.35 or epistemic > 0.15


class UncertaintyEstimator:
    """
    Quantifies predictive confidence using Split Conformal Prediction
    and Multi-Model Ensemble variance.
    """

    def __init__(self, confidence_level: float = 0.90):
        self.confidence_level = confidence_level
        self.alpha = 1.0 - confidence_level
        self.calibration_scores: List[float] = []
        self.quantile_threshold: float = 0.25
        self.is_calibrated = False

    def calibrate(self, val_probs: np.ndarray, val_targets: np.ndarray) -> "UncertaintyEstimator":
        """
        Calibrate non-conformity scores on unseen out-of-sample data.
        Non-conformity score: s_i = |y_i - p_i|
        """
        p = np.asarray(val_probs, dtype=np.float64).ravel()
        y = np.asarray(val_targets, dtype=np.float64).ravel()
        n = len(p)

        if n < 10:
            logger.warning("Insufficient validation samples for conformal calibration. Using default quantile.")
            self.quantile_threshold = 0.25
            self.is_calibrated = True
            return self

        # Non-conformity score: absolute error
        scores = np.abs(y - p)
        self.calibration_scores = sorted(scores.tolist())

        # Conformal quantile calculation with finite-sample correction
        # q_val = ceil((n + 1) * (1 - alpha)) / n
        q_idx = int(np.ceil((n + 1) * (1.0 - self.alpha))) - 1
        q_idx = min(max(0, q_idx), n - 1)
        self.quantile_threshold = float(self.calibration_scores[q_idx])
        self.is_calibrated = True

        logger.info(
            f"Conformal uncertainty calibrated on {n} samples: "
            f"Threshold={self.quantile_threshold:.4f} at {self.confidence_level*100:.0f}% confidence."
        )
        return self

    def estimate_uncertainty(
        self,
        calibrated_prob: float,
        model_probas: Optional[List[float]] = None,
    ) -> PredictionInterval:
        """
        Estimate prediction interval and decompose epistemic vs aleatoric uncertainty.
        """
        p = float(np.clip(calibrated_prob, 0.01, 0.99))

        # 1. Conformal bounds
        q = self.quantile_threshold if self.is_calibrated else 0.25
        lower = float(np.clip(p - q, 0.0, 1.0))
        upper = float(np.clip(p + q, 0.0, 1.0))
        width = round(upper - lower, 4)

        # 2. Epistemic Uncertainty (Ensemble variance)
        if model_probas and len(model_probas) > 1:
            epistemic = float(np.std(model_probas))
        else:
            epistemic = 0.05

        # 3. Aleatoric Uncertainty (Shannon Entropy)
        # H(p) = -p*log2(p) - (1-p)*log2(1-p)
        # Normalized by 1.0 (max entropy at p=0.5 is 1.0 bit)
        p_safe = np.clip(p, 1e-6, 1.0 - 1e-6)
        entropy = float(-p_safe * np.log2(p_safe) - (1.0 - p_safe) * np.log2(1.0 - p_safe))
        aleatoric = round(entropy, 4)

        is_high = bool(width > 0.40 or epistemic > 0.15 or (lower < 0.45 and upper > 0.55 and width > 0.30))

        return PredictionInterval(
            point_estimate=round(p, 4),
            lower_bound=round(lower, 4),
            upper_bound=round(upper, 4),
            interval_width=width,
            epistemic_uncertainty=round(epistemic, 4),
            aleatoric_uncertainty=aleatoric,
            confidence_level=self.confidence_level,
            is_high_uncertainty=is_high,
        )

    def save(self, filepath: str) -> None:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        joblib.dump(
            {
                "confidence_level": self.confidence_level,
                "alpha": self.alpha,
                "quantile_threshold": self.quantile_threshold,
                "is_calibrated": self.is_calibrated,
            },
            filepath,
        )

    def load(self, filepath: str) -> None:
        if os.path.exists(filepath):
            data = joblib.load(filepath)
            self.confidence_level = data["confidence_level"]
            self.alpha = data["alpha"]
            self.quantile_threshold = data["quantile_threshold"]
            self.is_calibrated = data["is_calibrated"]
