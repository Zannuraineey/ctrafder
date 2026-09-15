"""
Asynchronous Multi-Market Scanner & Opportunity Ranking Engine.
Section 7, 9, and 26 of project.md.
"""

from typing import Dict, List, Optional, Tuple
import asyncio
from datetime import datetime
from loguru import logger
import pandas as pd

from app.broker.models import (
    SymbolSpecification,
    Tick,
    Candle,
    TradeSignal,
    AIDecisionObject,
    MarketRegime,
)
from app.market.candles import CandleBuffer
from app.market.symbols import SymbolRegistry
from app.features.feature_pipeline import FeaturePipeline
from app.strategies.router import StrategyRouter
from app.ai.inference import AIInferenceEngine


class MarketOpportunity:
    """A ranked trading opportunity combining signal, AI decision, and ranking score."""

    def __init__(
        self,
        symbol: str,
        signal: TradeSignal,
        ai_decision: AIDecisionObject,
        score: float,
        features_df: pd.DataFrame,
    ):
        self.symbol = symbol
        self.signal = signal
        self.ai_decision = ai_decision
        self.score = score
        self.features_df = features_df


class MultiMarketScanner:
    """
    Concurrent multi-market scanner processing tick streams,
    generating features, running strategies and ranking candidate setups.
    """

    def __init__(
        self,
        symbol_registry: SymbolRegistry,
        strategy_router: StrategyRouter,
        ai_engine: AIInferenceEngine,
    ):
        self.registry = symbol_registry
        self.router = strategy_router
        self.ai_engine = ai_engine

        # Map of symbol -> CandleBuffer for 1m, 5m
        self.buffers_1m: Dict[str, CandleBuffer] = {}
        self.buffers_5m: Dict[str, CandleBuffer] = {}

        # Latest market states for UI/monitoring
        self.latest_regimes: Dict[str, Tuple[MarketRegime, float]] = {}
        self.latest_ai_decisions: Dict[str, AIDecisionObject] = {}

    def register_symbol(self, spec: SymbolSpecification) -> None:
        self.registry.register_symbol(spec)
        if spec.symbol not in self.buffers_1m:
            self.buffers_1m[spec.symbol] = CandleBuffer(spec.symbol, timeframe="1m")
            self.buffers_5m[spec.symbol] = CandleBuffer(spec.symbol, timeframe="5m")

    def ingest_tick(self, tick: Tick) -> None:
        """Feed real-time tick into market buffers."""
        sym = tick.symbol
        if sym not in self.buffers_1m:
            spec = self.registry.get_symbol(sym)
            if spec:
                self.register_symbol(spec)
            else:
                self.buffers_1m[sym] = CandleBuffer(sym, "1m")
                self.buffers_5m[sym] = CandleBuffer(sym, "5m")

        self.buffers_1m[sym].on_tick(tick)
        self.buffers_5m[sym].on_tick(tick)

    def load_historical_candles(self, symbol: str, candles_1m: List[Candle]) -> None:
        """Seed buffers with historical candles."""
        if symbol not in self.buffers_1m:
            self.buffers_1m[symbol] = CandleBuffer(symbol, "1m")
            self.buffers_5m[symbol] = CandleBuffer(symbol, "5m")
        self.buffers_1m[symbol].add_candles_bulk(candles_1m)

    def scan_symbol(self, symbol: str) -> Optional[MarketOpportunity]:
        """
        Evaluate a single symbol across features, regime, strategies, and AI scoring.
        """
        buf_1m = self.buffers_1m.get(symbol)
        if not buf_1m:
            return None

        candles_1m = buf_1m.get_all_candles(include_current=True)
        if len(candles_1m) < 25:
            return None

        spec = self.registry.get_symbol(symbol)
        if not spec:
            return None

        # 1. Compute Features
        df_1m = FeaturePipeline.candles_to_dataframe(candles_1m)
        features_1m = FeaturePipeline.compute_all_features(df_1m)

        # Context features (5m)
        features_5m = None
        buf_5m = self.buffers_5m.get(symbol)
        if buf_5m:
            c5m = buf_5m.get_all_candles(include_current=True)
            if len(c5m) >= 10:
                df_5m = FeaturePipeline.candles_to_dataframe(c5m)
                features_5m = FeaturePipeline.compute_all_features(df_5m)

        # 2. Detect Market Regime
        from app.ai.regime.detector import RegimeDetector
        regime, regime_conf = RegimeDetector.detect_regime(features_1m)
        self.latest_regimes[symbol] = (regime, regime_conf)

        # 3. Route to Strategies
        candidate_signals = self.router.route_and_evaluate(
            symbol=symbol,
            features_df=features_1m,
            regime=regime,
            spec=spec,
            higher_tf_features_df=features_5m,
        )

        if not candidate_signals:
            # Record neutral AI state
            neutral_decision = self.ai_engine.evaluate_market_and_signal(
                symbol=symbol,
                features_df=features_1m,
                candidate_signal=None,
                spec=spec,
            )
            self.latest_ai_decisions[symbol] = neutral_decision
            return None

        # Pick best strategy signal
        best_signal = candidate_signals[0]

        # 4. Run AI Evaluation
        ai_decision = self.ai_engine.evaluate_market_and_signal(
            symbol=symbol,
            features_df=features_1m,
            candidate_signal=best_signal,
            spec=spec,
        )
        self.latest_ai_decisions[symbol] = ai_decision

        # 5. Opportunity Score Calculation (Section 26 of project.md)
        # Score combines Win Probability, Trade Quality, Whipsaw Safety, and Expected R:R
        win_prob = max(ai_decision.buy_probability, ai_decision.sell_probability)
        whipsaw_safety = 1.0 - ai_decision.whipsaw_probability
        opportunity_score = (
            (win_prob * 0.45)
            + (ai_decision.trade_quality * 0.35)
            + (whipsaw_safety * 0.20)
        )

        return MarketOpportunity(
            symbol=symbol,
            signal=best_signal,
            ai_decision=ai_decision,
            score=round(opportunity_score, 4),
            features_df=features_1m,
        )

    def scan_all_markets(self) -> List[MarketOpportunity]:
        """
        Scan all configured symbols concurrently and return ranked opportunities.
        """
        symbols = list(self.buffers_1m.keys())
        opportunities: List[MarketOpportunity] = []

        for sym in symbols:
            try:
                opp = self.scan_symbol(sym)
                if opp:
                    opportunities.append(opp)
            except Exception as e:
                logger.error(f"Error scanning {sym}: {e}")

        # Rank by opportunity score descending
        opportunities.sort(key=lambda x: x.score, reverse=True)
        return opportunities
