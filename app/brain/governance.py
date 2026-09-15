"""
Model Governance, Drift Detection, and Rollback Control Engine.
Tracks model lifecycle, computes Kolmogorov-Smirnov feature drift statistics,
and enforces automated circuit breakers when live performance deviates from validation bounds.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import numpy as np
import scipy.stats as stats
from loguru import logger


@dataclass
class ModelVersionRecord:
    version_id: str
    model_name: str
    model_hash: str
    created_at: datetime
    val_accuracy: float
    val_roc_auc: float
    val_brier_score: float
    is_active: bool = True
    status: str = "PRODUCTION"   # PRODUCTION, SHADOW, DEPRECATED, ROLLED_BACK


@dataclass
class DriftReport:
    timestamp: datetime
    is_drift_detected: bool
    feature_ks_pvalues: Dict[str, float]
    drifted_features: List[str]
    alert_level: str  # NORMAL, WARNING, CRITICAL


class ModelGovernanceRegistry:
    """
    Manages versioning, feature drift auditing, and performance circuit breakers.
    """

    def __init__(self, drift_alpha: float = 0.05):
        self.drift_alpha = drift_alpha
        self.version_history: List[ModelVersionRecord] = []
        self.active_version: Optional[ModelVersionRecord] = None
        self.reference_features: Dict[str, np.ndarray] = {}
        self.live_feature_buffer: Dict[str, List[float]] = {}
        self.is_circuit_breaker_tripped = False

    def register_production_model(
        self,
        model_name: str,
        model_bytes: bytes,
        val_accuracy: float,
        val_roc_auc: float,
        val_brier_score: float,
        reference_data: Optional[Dict[str, np.ndarray]] = None,
    ) -> ModelVersionRecord:
        """
        Register and promote a verified model to active production.
        """
        model_hash = hashlib.sha256(model_bytes).hexdigest()[:16]
        version_id = f"{model_name}_v{len(self.version_history)+1}_{datetime.now(timezone.utc).strftime('%Y%m%d')}"

        record = ModelVersionRecord(
            version_id=version_id,
            model_name=model_name,
            model_hash=model_hash,
            created_at=datetime.now(timezone.utc),
            val_accuracy=round(val_accuracy, 4),
            val_roc_auc=round(val_roc_auc, 4),
            val_brier_score=round(val_brier_score, 4),
            is_active=True,
            status="PRODUCTION",
        )

        # Deactivate older production models of the same name
        for v in self.version_history:
            if v.model_name == model_name and v.is_active:
                v.is_active = False
                v.status = "DEPRECATED"

        self.version_history.append(record)
        self.active_version = record
        if reference_data:
            self.reference_features = reference_data
            self.live_feature_buffer = {k: [] for k in reference_data}

        logger.info(
            f"[GOVERNANCE] Model {version_id} ({model_hash}) registered to PRODUCTION. "
            f"Val AUC={val_roc_auc:.3f}, Brier={val_brier_score:.3f}"
        )
        return record

    def record_live_features(self, feature_row: Dict[str, float]) -> None:
        """Append live inference features to audit buffer for drift testing."""
        for feat_name, val in feature_row.items():
            if feat_name in self.reference_features:
                buf = self.live_feature_buffer.setdefault(feat_name, [])
                buf.append(float(val))
                if len(buf) > 500:
                    buf.pop(0)

    def check_covariate_drift(self) -> DriftReport:
        """
        Perform Kolmogorov-Smirnov two-sample test comparing reference training features
        against live inference distributions.
        """
        now = datetime.now(timezone.utc)
        ks_pvals: Dict[str, float] = {}
        drifted: List[str] = []

        for feat_name, ref_arr in self.reference_features.items():
            live_arr = np.array(self.live_feature_buffer.get(feat_name, []))
            if len(live_arr) < 30 or len(ref_arr) < 30:
                continue

            stat, p_val = stats.ks_2samp(ref_arr, live_arr)
            ks_pvals[feat_name] = round(float(p_val), 4)
            if p_val < self.drift_alpha:
                drifted.append(feat_name)

        is_drift = len(drifted) >= max(1, len(self.reference_features) // 3)
        alert = "CRITICAL" if len(drifted) >= len(self.reference_features) // 2 else "WARNING" if is_drift else "NORMAL"

        report = DriftReport(
            timestamp=now,
            is_drift_detected=is_drift,
            feature_ks_pvalues=ks_pvals,
            drifted_features=drifted,
            alert_level=alert,
        )

        if is_drift:
            logger.warning(
                f"[DRIFT DETECTED] {len(drifted)} features drifted: {drifted}. Alert Level: {alert}"
            )
        return report

    def evaluate_circuit_breaker(
        self,
        recent_win_rate: float,
        recent_brier_score: float,
        n_trades: int,
    ) -> bool:
        """
        Enforce performance circuit breaker.
        Trips if live win rate collapses or Brier score indicates high predictive error.
        """
        if n_trades < 10:
            return False

        if recent_win_rate < 0.35 or recent_brier_score > 0.30:
            self.is_circuit_breaker_tripped = True
            if self.active_version:
                self.active_version.status = "ROLLED_BACK"
                self.active_version.is_active = False
            logger.critical(
                f"[CIRCUIT BREAKER TRIPPED] Model performance degraded (WinRate={recent_win_rate*100:.1f}%, "
                f"Brier={recent_brier_score:.3f}). Tripping governance circuit breaker and reverting to conservative prior!"
            )
            return True

        self.is_circuit_breaker_tripped = False
        return False
