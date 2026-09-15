"""
Strategy #2: Volatility Breakout + Retest Strategy.
Implements breakout from consolidation with retest confirmation from strategy.md Section 12 & 13.
"""

from typing import Optional
import pandas as pd
from datetime import datetime

from app.broker.models import TradeSignal, TradeSide, SymbolSpecification, MarketRegime
from app.strategies.base import BaseStrategy


class VolatilityBreakoutStrategy(BaseStrategy):
    """
    Detects compression followed by expansion and retest of structure boundaries.
    """

    def __init__(self):
        super().__init__(name="VOLATILITY_BREAKOUT")

    def evaluate(
        self,
        symbol: str,
        features_df: pd.DataFrame,
        regime: MarketRegime,
        spec: SymbolSpecification,
        higher_tf_features_df: Optional[pd.DataFrame] = None,
    ) -> Optional[TradeSignal]:
        if len(features_df) < 30:
            return None

        curr = features_df.iloc[-1]
        prev = features_df.iloc[-2]
        lookback = features_df.iloc[-10:-2]

        close = curr["close"]
        atr = max(curr["atr_14"], spec.tick_size * 10)
        bandwidth = curr["bb_bandwidth"]
        expansion_ratio = curr["volatility_expansion_ratio"]

        # Consolidation check: Prior bars had low bandwidth or compression
        was_compressed = (lookback["bb_bandwidth"].min() < 0.05) or (expansion_ratio > 1.15)
        if not was_compressed:
            return None

        # ---------------- BULLISH BREAKOUT + RETEST ----------------
        swing_high = curr["swing_high_level"]
        # Breakout occurred recently and current bar retests and bounces off broken level
        broke_high = prev["high"] >= swing_high or curr["bos_bullish"] == 1
        retested_support = curr["low"] <= swing_high * 1.002 and close > swing_high

        if broke_high and retested_support and (curr["close_location_value"] > 0.3):
            sl_distance = max(1.5 * atr, (close - swing_high) + atr)
            stop_loss = round(close - sl_distance, spec.digits)
            take_profit = round(close + (sl_distance * 2.2), spec.digits)

            return TradeSignal(
                symbol=symbol,
                side=TradeSide.BUY,
                strategy=self.name,
                timeframe="1m",
                entry_price=close,
                stop_loss=stop_loss,
                take_profit=take_profit,
                timestamp=datetime.utcnow(),
                metadata={"type": "BULLISH_BREAKOUT_RETEST", "rr": 2.2},
            )

        # ---------------- BEARISH BREAKOUT + RETEST ----------------
        swing_low = curr["swing_low_level"]
        broke_low = prev["low"] <= swing_low or curr["bos_bearish"] == 1
        retested_resistance = curr["high"] >= swing_low * 0.998 and close < swing_low

        if broke_low and retested_resistance and (curr["close_location_value"] < -0.3):
            sl_distance = max(1.5 * atr, (swing_low - close) + atr)
            stop_loss = round(close + sl_distance, spec.digits)
            take_profit = round(close - (sl_distance * 2.2), spec.digits)

            return TradeSignal(
                symbol=symbol,
                side=TradeSide.SELL,
                strategy=self.name,
                timeframe="1m",
                entry_price=close,
                stop_loss=stop_loss,
                take_profit=take_profit,
                timestamp=datetime.utcnow(),
                metadata={"type": "BEARISH_BREAKOUT_RETEST", "rr": 2.2},
            )

        return None
