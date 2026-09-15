"""
AI Inference Engine.
Coordinates regime detection, whipsaw analysis, and ensemble model inference
to produce the standardized AIDecisionObject (project.md Section 72).
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import pandas as pd
import numpy as np

from app.broker.models import (
    Candle,
    TradeSignal,
    TradeSide,
    MarketRegime,
    AIDecisionObject,
    SymbolSpecification,
)
from app.features.feature_pipeline import FeaturePipeline, CANONICAL_FEATURE_COLS
from app.ai.regime.detector import RegimeDetector
from app.ai.whipsaw.detector import WhipsawDetector
from app.ai.ensemble.meta_model import EnsembleMetaModel
from app.ai.models.random_forest import RandomForestDirectionModel
from app.ai.models.xgboost_model import GradientBoostingDirectionModel
from app.ai.models.neural_network import NeuralNetworkPatternModel


class AIInferenceEngine:
    """
    Unified AI inference service producing AIDecisionObject with V2 Continuation & Momentum.
    """

    def __init__(self, ensemble: Optional[EnsembleMetaModel] = None):
        if ensemble is None:
            # Default institutional ensemble: Random Forest + Gradient Boosting + Deep Neural Network
            rf = RandomForestDirectionModel()
            gb = GradientBoostingDirectionModel()
            nn = NeuralNetworkPatternModel()
            self.ensemble = EnsembleMetaModel([rf, gb, nn])
        else:
            self.ensemble = ensemble

    def evaluate_market_and_signal(
        self,
        symbol: str,
        features_df: pd.DataFrame,
        candidate_signal: Optional[TradeSignal],
        spec: SymbolSpecification,
    ) -> AIDecisionObject:
        """
        Produce a normalized AIDecisionObject from current market features,
        momentum score, volume pressure, and continuation probability.
        """
        now = datetime.utcnow()
        from app.market.volume_pressure import VolumePressureEngine
        from app.market.momentum_engine import AdvancedMomentumEngine
        from app.execution.continuation_engine import ContinuationEngine, LifecycleAction

        if features_df.empty or len(features_df) < 15:
            return AIDecisionObject(
                symbol=symbol,
                timestamp=now,
                direction=None,
                no_trade_probability=1.0,
                trade_quality=0.0,
                regime=MarketRegime.UNKNOWN,
                whipsaw_probability=1.0,
                momentum_score=50.0,
                volume_pressure=1.0,
                continuation_probability=0.0,
                lifecycle_action="EXIT",
            )

        # 1. Detect Regime
        regime, regime_conf = RegimeDetector.detect_regime(features_df)

        # If no candidate setup proposed by strategy router, return neutral market state
        if candidate_signal is None:
            vol_m = VolumePressureEngine.analyze(features_df)
            mom_m = AdvancedMomentumEngine.analyze(features_df)
            return AIDecisionObject(
                symbol=symbol,
                timestamp=now,
                direction=None,
                buy_probability=0.0,
                sell_probability=0.0,
                no_trade_probability=1.0,
                trade_quality=0.0,
                regime=regime,
                regime_confidence=regime_conf,
                whipsaw_probability=0.0,
                strategy="NO_SETUP",
                momentum_score=mom_m.momentum_score,
                momentum_state=mom_m.state.value,
                volume_pressure=vol_m.rvol,
                volume_state=vol_m.volume_state.value,
                continuation_probability=0.50,
                lifecycle_action="EXIT",
            )

        # 2. Calculate Whipsaw Probability
        whipsaw_prob = WhipsawDetector.calculate_whipsaw_probability(
            features_df, candidate_signal.side, regime
        )

        # 3. Calculate Continuation Engine & Market Force Metrics (strategy.md & project.md V2)
        cont_eval = ContinuationEngine.evaluate_setup(features_df, candidate_signal.side)
        mom = cont_eval.momentum_metrics
        vol = cont_eval.volume_metrics

        # 4. Calculate Expected R:R
        risk_dist = abs(candidate_signal.entry_price - candidate_signal.stop_loss)
        reward_dist = abs(candidate_signal.take_profit - candidate_signal.entry_price)
        expected_rr = (reward_dist / risk_dist) if risk_dist > 0 else 1.5

        # 5. Extract Feature Row for ML Model
        latest_row = features_df.iloc[-1:]
        available_cols = [c for c in CANONICAL_FEATURE_COLS if c in latest_row.columns]
        X = latest_row[available_cols].fillna(0.0)

        # 6. Run Ensemble Prediction
        win_prob, base_quality, calibrated_score = self.ensemble.predict_direction_and_quality(
            X=X,
            candidate_side=candidate_signal.side,
            regime=regime,
            whipsaw_prob=whipsaw_prob,
            expected_rr=expected_rr,
        )

        # Blend base AI quality with Continuation Probability (project.md Section 7)
        # Quality = 50% ML Model Quality + 50% Continuation Probability
        final_trade_quality = round((base_quality * 0.50) + (cont_eval.continuation_probability * 0.50), 2)

        # Calculate directional probabilities
        if candidate_signal.side == TradeSide.BUY:
            buy_prob = round(win_prob * 0.6 + cont_eval.continuation_probability * 0.4, 4)
            sell_prob = round((1.0 - buy_prob) * 0.35, 4)
            no_trade_prob = round(1.0 - buy_prob - sell_prob, 4)
        else:
            sell_prob = round(win_prob * 0.6 + cont_eval.continuation_probability * 0.4, 4)
            buy_prob = round((1.0 - sell_prob) * 0.35, 4)
            no_trade_prob = round(1.0 - sell_prob - buy_prob, 4)

        return AIDecisionObject(
            symbol=symbol,
            timestamp=now,
            direction=candidate_signal.side if cont_eval.lifecycle_action == LifecycleAction.ENTER else None,
            buy_probability=max(0.0, buy_prob),
            sell_probability=max(0.0, sell_prob),
            no_trade_probability=max(0.0, no_trade_prob),
            trade_quality=final_trade_quality,
            regime=regime,
            regime_confidence=regime_conf,
            whipsaw_probability=whipsaw_prob,
            expected_duration_seconds=60,
            expected_rr=round(expected_rr, 2),
            strategy=candidate_signal.strategy,
            model_version="ensemble_v2_continuation",
            raw_scores={
                "calibrated_score": calibrated_score,
                "continuation_score": cont_eval.continuation_score,
                "participation_score": vol.participation_score,
                "uncertainty_lower": getattr(self.ensemble.last_uncertainty, "lower_bound", round(max(0.0, win_prob - 0.15), 2)),
                "uncertainty_upper": getattr(self.ensemble.last_uncertainty, "upper_bound", round(min(1.0, win_prob + 0.15), 2)),
                "epistemic_uncertainty": getattr(self.ensemble.last_uncertainty, "epistemic_uncertainty", 0.05),
                "aleatoric_uncertainty": getattr(self.ensemble.last_uncertainty, "aleatoric_uncertainty", 0.95),
            },
            momentum_score=mom.momentum_score,
            momentum_state=mom.state.value,
            volume_pressure=vol.rvol,
            volume_state=vol.volume_state.value,
            continuation_probability=cont_eval.continuation_probability,
            lifecycle_action=cont_eval.lifecycle_action.value,
        )
