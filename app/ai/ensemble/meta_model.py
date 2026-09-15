"""
Ensemble Meta-Model: Aggregates model probabilities and calibrates trade quality
via learned Stacking Meta-Learner (app.brain.meta_learner).
"""

from typing import List, Dict, Any, Tuple, Optional, TYPE_CHECKING
import pandas as pd
import numpy as np

from app.ai.models.base import BaseMLModel
from app.broker.models import TradeSide, MarketRegime
from app.brain.uncertainty import PredictionInterval

if TYPE_CHECKING:
    from app.brain.meta_learner import LearnedMetaModel


class EnsembleMetaModel:
    """
    Ensemble predictor combining multiple model probabilities via an empirically
    trained Stacking Meta-Learner with probability calibration and conformal uncertainty.
    """

    def __init__(self, models: Optional[List[BaseMLModel]] = None):
        from app.brain.meta_learner import LearnedMetaModel
        self.models: List[BaseMLModel] = models or []
        self.learned_meta = LearnedMetaModel(base_models=self.models)
        self.last_uncertainty: Optional[PredictionInterval] = None

    def add_model(self, model: BaseMLModel) -> None:
        self.models.append(model)
        self.learned_meta.add_model(model)

    def predict_direction_and_quality(
        self,
        X: pd.DataFrame,
        candidate_side: TradeSide,
        regime: MarketRegime,
        whipsaw_prob: float,
        expected_rr: float,
    ) -> Tuple[float, float, float]:
        """
        Evaluate candidate setup via learned stacking meta-model.
        Returns:
            win_probability: float (0.0 to 1.0)
            trade_quality: float (0.0 to 1.0)
            calibrated_score: float
        """
        win_prob, trade_quality, calibrated_score, uncertainty = self.learned_meta.predict_direction_and_quality(
            X=X,
            candidate_side=candidate_side,
            regime=regime,
            whipsaw_prob=whipsaw_prob,
            expected_rr=expected_rr,
        )
        self.last_uncertainty = uncertainty
        return win_prob, trade_quality, calibrated_score
