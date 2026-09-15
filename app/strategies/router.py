"""
Strategy Router: Maps market regime and instrument family to appropriate strategies.
Implements the architecture from strategy.md Section 9, 21, and 29.
"""

from typing import List, Optional, Dict
import pandas as pd
from loguru import logger

from app.broker.models import TradeSignal, SymbolSpecification, MarketRegime
from app.strategies.base import BaseStrategy
from app.strategies.trend_pullback import TrendPullbackStrategy
from app.strategies.volatility_breakout import VolatilityBreakoutStrategy
from app.strategies.momentum import MomentumStrategy
from app.strategies.mean_reversion import MeanReversionStrategy
from app.strategies.synthetic.volatility_indices import DerivVolatilityStrategy
from app.strategies.synthetic.range_break import RangeBreakStrategy
from app.strategies.synthetic.crash_boom import CrashBoomStrategy
from app.strategies.institutional_sweep import InstitutionalLiquiditySweepStrategy
from app.strategies.poc_strategy import POCReactionStrategy


class StrategyRouter:
    """
    Intelligent router selecting and running the appropriate strategies
    based on market regime and instrument specialization.
    """

    def __init__(self):
        # Instantiate available strategy pool
        self.trend_pullback = TrendPullbackStrategy()
        self.volatility_breakout = VolatilityBreakoutStrategy()
        self.momentum = MomentumStrategy()
        self.mean_reversion = MeanReversionStrategy()
        self.deriv_volatility = DerivVolatilityStrategy()
        self.range_break = RangeBreakStrategy()
        self.crash_boom = CrashBoomStrategy()
        self.institutional_sweep = InstitutionalLiquiditySweepStrategy()
        self.poc_reaction = POCReactionStrategy()

    def route_and_evaluate(
        self,
        symbol: str,
        features_df: pd.DataFrame,
        regime: MarketRegime,
        spec: SymbolSpecification,
        higher_tf_features_df: Optional[pd.DataFrame] = None,
    ) -> List[TradeSignal]:
        """
        Determine eligible strategies for the symbol and regime, execute them,
        and return candidate signals.
        """
        candidates: List[TradeSignal] = []
        sym_lower = symbol.lower()
        asset_class = spec.asset_class.upper()

        # 1. Specialized Synthetic Indices routing
        if asset_class == "SYNTHETIC" or any(k in sym_lower for k in ["volatility", "range", "crash", "boom", "step", "jump"]):
            if "range" in sym_lower:
                sig = self.range_break.evaluate(symbol, features_df, regime, spec, higher_tf_features_df)
                if sig:
                    candidates.append(sig)
            elif "crash" in sym_lower or "boom" in sym_lower:
                sig = self.crash_boom.evaluate(symbol, features_df, regime, spec, higher_tf_features_df)
                if sig:
                    candidates.append(sig)
            else:
                sig = self.deriv_volatility.evaluate(symbol, features_df, regime, spec, higher_tf_features_df)
                if sig:
                    candidates.append(sig)

        # 2. General Market (Forex, Metals, Crypto, Indices) & Synthetic Trend/Breakout Routing
        strategies_to_run: List[BaseStrategy] = []

        if regime in (MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN):
            strategies_to_run.extend([self.trend_pullback, self.momentum, self.institutional_sweep, self.poc_reaction])
        elif regime in (MarketRegime.BREAKOUT, MarketRegime.CHOPPY):
            strategies_to_run.extend([self.volatility_breakout, self.momentum, self.institutional_sweep, self.poc_reaction])
        elif regime in (MarketRegime.RANGING, MarketRegime.LOW_VOLATILITY):
            # Run mean reversion, liquidity sweep, and POC reaction inside ranges
            strategies_to_run.extend([self.mean_reversion, self.institutional_sweep, self.poc_reaction])
        elif regime == MarketRegime.HIGH_VOLATILITY:
            strategies_to_run.extend([self.volatility_breakout, self.momentum, self.institutional_sweep, self.poc_reaction])

        for strat in strategies_to_run:
            try:
                sig = strat.evaluate(symbol, features_df, regime, spec, higher_tf_features_df)
                if sig:
                    candidates.append(sig)
            except Exception as e:
                logger.error(f"Strategy {strat.name} error on {symbol}: {e}")

        return candidates
