"""
Antigravity Quant Quantitative Brain Package.
Houses learned meta-models, probability calibration, uncertainty estimation,
and statistical regime classification.
"""

from app.brain.calibration import ProbabilityCalibrator, CalibrationMetrics
from app.brain.uncertainty import UncertaintyEstimator, PredictionInterval
from app.brain.meta_learner import LearnedMetaModel
from app.brain.regime_classifier import StatisticalRegimeClassifier

__all__ = [
    "ProbabilityCalibrator",
    "CalibrationMetrics",
    "UncertaintyEstimator",
    "PredictionInterval",
    "LearnedMetaModel",
    "StatisticalRegimeClassifier",
]
