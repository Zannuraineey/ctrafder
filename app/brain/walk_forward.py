"""
Walk-Forward Validation Engine with Purged and Embargoed Time-Series Cross-Validation.
Implements Marcos López de Prado's PurgedGroupTimeSeriesSplit to eliminate lookahead bias
and serial correlation leakage from overlapping multi-bar forward labels.
"""

from typing import Generator, List, Tuple, Optional, Dict, Any
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, precision_score, roc_auc_score, brier_score_loss
from loguru import logger


class PurgedTimeSeriesSplit:
    """
    Time-Series Cross-Validation with Purging and Embargo.
    - Purging: Drops training observations whose forward-looking evaluation window
      overlaps with test samples.
    - Embargo: Drops training observations immediately following test sets to prevent
      autoregressive memory contamination.
    """

    def __init__(
        self,
        n_splits: int = 4,
        max_train_size: Optional[int] = None,
        purge_window: int = 5,
        embargo_pct: float = 0.02,
    ):
        self.n_splits = n_splits
        self.max_train_size = max_train_size
        self.purge_window = purge_window
        self.embargo_pct = embargo_pct

    def split(
        self,
        X: np.ndarray,
        y: Optional[np.ndarray] = None,
    ) -> Generator[Tuple[np.ndarray, np.ndarray], None, None]:
        """
        Generate indices for train and test splits with strict purging.
        """
        n_samples = len(X)
        test_size = n_samples // (self.n_splits + 1)
        embargo_bars = int(n_samples * self.embargo_pct)

        for i in range(self.n_splits):
            test_start = (i + 1) * test_size
            test_end = min(test_start + test_size, n_samples)
            test_indices = np.arange(test_start, test_end)

            # Training set is strictly historical to the test set
            train_end = max(0, test_start - self.purge_window)
            train_start = 0 if self.max_train_size is None else max(0, train_end - self.max_train_size)

            train_indices = np.arange(train_start, train_end)

            if len(train_indices) >= 15 and len(test_indices) >= 5:
                yield train_indices, test_indices


class WalkForwardValidator:
    """
    Executes walk-forward model validation across sequential purged market regimes.
    """

    @classmethod
    def validate_model(
        cls,
        model_cls: Any,
        model_kwargs: Dict[str, Any],
        X: pd.DataFrame,
        y: pd.Series,
        n_splits: int = 4,
        purge_window: int = 5,
    ) -> Dict[str, Any]:
        """
        Run Purged Walk-Forward Cross-Validation and return robust performance metrics.
        """
        splitter = PurgedTimeSeriesSplit(n_splits=n_splits, purge_window=purge_window)
        X_arr = X.to_numpy()
        y_arr = y.to_numpy(dtype=np.int32)

        fold_accuracies: List[float] = []
        fold_aucs: List[float] = []
        fold_briers: List[float] = []

        for fold_idx, (train_idx, test_idx) in enumerate(splitter.split(X_arr, y_arr)):
            X_tr, y_tr = X.iloc[train_idx], y.iloc[train_idx]
            X_te, y_te = X.iloc[test_idx], y.iloc[test_idx]

            if len(np.unique(y_tr)) < 2:
                continue

            instance = model_cls(**model_kwargs)
            instance.train(X_tr, y_tr)

            preds_proba = instance.predict_proba(X_te)[:, 1]
            preds = (preds_proba >= 0.50).astype(int)

            acc = float(accuracy_score(y_te, preds))
            brier = float(brier_score_loss(y_te, preds_proba))
            auc = (
                float(roc_auc_score(y_te, preds_proba))
                if len(np.unique(y_te)) > 1
                else 0.50
            )

            fold_accuracies.append(acc)
            fold_aucs.append(auc)
            fold_briers.append(brier)

        avg_acc = float(np.mean(fold_accuracies)) if fold_accuracies else 0.50
        avg_auc = float(np.mean(fold_aucs)) if fold_aucs else 0.50
        avg_brier = float(np.mean(fold_briers)) if fold_briers else 0.25

        logger.info(
            f"[PURGED WALK-FORWARD] {len(fold_accuracies)} folds evaluated: "
            f"Mean Accuracy={avg_acc:.3f}, Mean ROC-AUC={avg_auc:.3f}, Mean Brier={avg_brier:.3f}"
        )

        return {
            "folds_evaluated": len(fold_accuracies),
            "mean_accuracy": round(avg_acc, 4),
            "mean_roc_auc": round(avg_auc, 4),
            "mean_brier_score": round(avg_brier, 4),
            "is_stable": bool(avg_auc >= 0.52 and avg_brier <= 0.25),
        }
