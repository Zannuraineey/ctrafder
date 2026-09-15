"""
Statistical Market Regime Classifier.
Replaces arbitrary heuristic thresholds with an unsupervised Gaussian Mixture Model (GMM)
and statistical time-series metrics (Hurst exponent proxy, realized volatility, return autocorrelation).
"""

from typing import Tuple, Dict, Any, Optional
import os
import numpy as np
import pandas as pd
import joblib
from sklearn.mixture import GaussianMixture
from loguru import logger

from app.broker.models import MarketRegime


class StatisticalRegimeClassifier:
    """
    Classifies latent market regimes using Gaussian Mixture Models (GMM)
    trained on multi-scale statistical features:
    - Realized Volatility & Garman-Klass Volatility
    - Return Autocorrelation (Persistence vs Mean-Reversion)
    - Variance Ratio (Random walk vs Trend/Chop)
    - Volume-Expansion Ratio
    """

    def __init__(self, n_components: int = 4, random_state: int = 42):
        self.n_components = n_components
        self.gmm = GaussianMixture(
            n_components=n_components,
            covariance_type="full",
            max_iter=200,
            random_state=random_state,
        )
        self.is_fitted = False
        self._cluster_to_regime_map: Dict[int, MarketRegime] = {}

    def extract_statistical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute normalized statistical market features from OHLCV bars.
        """
        if df.empty or len(df) < 15:
            return pd.DataFrame()

        close = df["close"].to_numpy(dtype=np.float64)
        high = df["high"].to_numpy(dtype=np.float64)
        low = df["low"].to_numpy(dtype=np.float64)
        vol = df["volume"].to_numpy(dtype=np.float64) if "volume" in df else np.ones(len(df))

        # 1. Log returns
        returns = np.diff(np.log(close), prepend=np.log(close[0]))

        # 2. Realized Volatility (14-bar rolling std dev)
        r_series = pd.Series(returns)
        realized_vol = r_series.rolling(14, min_periods=5).std().fillna(0.001).to_numpy()

        # 3. Garman-Klass Volatility (incorporating High/Low range)
        log_hl = np.log(high / np.maximum(low, 1e-9))
        log_co = np.log(close / np.maximum(df["open"].to_numpy(dtype=np.float64), 1e-9))
        gk_vol = np.sqrt(0.5 * (log_hl ** 2) - (2.0 * np.log(2.0) - 1.0) * (log_co ** 2))
        gk_vol_smooth = pd.Series(gk_vol).rolling(14, min_periods=5).mean().fillna(0.001).to_numpy()

        # 4. Return Autocorrelation (Lag 1) over 20 bars
        autocorr_20 = (
            r_series.rolling(20, min_periods=10)
            .apply(lambda s: s.autocorr(lag=1) if len(s) > 1 else 0.0, raw=False)
            .fillna(0.0)
            .to_numpy()
        )

        # 5. Variance Ratio Proxy: Var(r_2) / (2 * Var(r_1))
        r2 = pd.Series(np.diff(np.log(close[::2]), prepend=np.log(close[0])) if len(close) > 2 else returns)
        var_1 = r_series.rolling(20, min_periods=5).var().fillna(1e-6)
        var_2 = r2.rolling(10, min_periods=3).var().fillna(1e-6)
        vr_ratio = (var_2 / (2.0 * np.maximum(var_1, 1e-9))).clip(0.1, 5.0).to_numpy()

        # 6. Volume Relative Expansion
        vol_s = pd.Series(vol)
        vol_ma = vol_s.rolling(20, min_periods=5).mean().fillna(1.0)
        vol_expansion = (vol_s / np.maximum(vol_ma, 1e-9)).clip(0.1, 10.0).to_numpy()

        feat_df = pd.DataFrame({
            "realized_vol": realized_vol,
            "gk_vol": gk_vol_smooth,
            "autocorr": autocorr_20,
            "variance_ratio": vr_ratio,
            "vol_expansion": vol_expansion,
        })
        return feat_df

    def fit(self, historical_df: pd.DataFrame) -> "StatisticalRegimeClassifier":
        """
        Fit Gaussian Mixture Model on historical features and map clusters to market regimes.
        """
        feats = self.extract_statistical_features(historical_df)
        if len(feats) < 30:
            logger.warning("Insufficient data to fit statistical GMM regime classifier.")
            return self

        X = feats.dropna().to_numpy()
        self.gmm.fit(X)
        self.is_fitted = True

        # Map mixture components based on cluster means
        # Means: [realized_vol, gk_vol, autocorr, variance_ratio, vol_expansion]
        means = self.gmm.means_
        for cluster_idx in range(self.n_components):
            c_mean = means[cluster_idx]
            vol_lvl = c_mean[0]
            autocorr_lvl = c_mean[2]
            exp_lvl = c_mean[4]

            if exp_lvl > 1.5 and vol_lvl > np.median(means[:, 0]):
                self._cluster_to_regime_map[cluster_idx] = MarketRegime.BREAKOUT
            elif vol_lvl > np.percentile(means[:, 0], 70):
                self._cluster_to_regime_map[cluster_idx] = MarketRegime.HIGH_VOLATILITY
            elif autocorr_lvl > 0.05:
                # Direction determined dynamically at inference time (Up vs Down)
                self._cluster_to_regime_map[cluster_idx] = MarketRegime.TRENDING_UP
            else:
                self._cluster_to_regime_map[cluster_idx] = MarketRegime.CHOPPY

        logger.info(f"Statistical GMM Regime Classifier fitted with {self.n_components} components.")
        return self

    def classify_regime(self, df: pd.DataFrame) -> Tuple[MarketRegime, float]:
        """
        Classify current market regime and return (MarketRegime, Bayesian posterior confidence).
        """
        if df.empty or len(df) < 15:
            return MarketRegime.UNKNOWN, 0.0

        close = df["close"].to_numpy(dtype=np.float64)
        curr_close = close[-1]
        sma_50 = float(np.mean(close[-min(50, len(close)):]))

        if not self.is_fitted:
            # Fallback to empirical moment estimation
            returns = np.diff(np.log(close[-15:]))
            vol = float(np.std(returns)) if len(returns) > 1 else 0.005
            autocorr = float(pd.Series(returns).autocorr(lag=1)) if len(returns) > 4 else 0.0

            if vol > 0.02:
                return MarketRegime.HIGH_VOLATILITY, 0.75
            elif autocorr > 0.10:
                reg = MarketRegime.TRENDING_UP if curr_close >= sma_50 else MarketRegime.TRENDING_DOWN
                return reg, 0.70
            elif autocorr < -0.15:
                return MarketRegime.CHOPPY, 0.65
            else:
                return MarketRegime.RANGING, 0.60

        feats = self.extract_statistical_features(df)
        latest_x = feats.iloc[-1:].to_numpy()

        try:
            posteriors = self.gmm.predict_proba(latest_x)[0]
            best_cluster = int(np.argmax(posteriors))
            confidence = float(posteriors[best_cluster])
            base_regime = self._cluster_to_regime_map.get(best_cluster, MarketRegime.RANGING)

            # Resolve directional trend (Up vs Down) using EMA alignment
            if base_regime in (MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN):
                if curr_close >= sma_50:
                    return MarketRegime.TRENDING_UP, round(confidence, 2)
                else:
                    return MarketRegime.TRENDING_DOWN, round(confidence, 2)

            return base_regime, round(confidence, 2)
        except Exception as e:
            logger.warning(f"GMM regime classification failed: {e}")
            return MarketRegime.RANGING, 0.50

    def save(self, filepath: str) -> None:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        joblib.dump(
            {
                "n_components": self.n_components,
                "gmm": self.gmm,
                "is_fitted": self.is_fitted,
                "cluster_map": self._cluster_to_regime_map,
            },
            filepath,
        )

    def load(self, filepath: str) -> None:
        if os.path.exists(filepath):
            data = joblib.load(filepath)
            self.n_components = data["n_components"]
            self.gmm = data["gmm"]
            self.is_fitted = data["is_fitted"]
            self._cluster_to_regime_map = data["cluster_map"]
