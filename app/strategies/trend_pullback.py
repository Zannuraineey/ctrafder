"""
Primary Strategy #1: Regime-Aware Trend Pullback Strategy.
Implements the multi-timeframe trend pullback architecture from strategy.md Section 10 & 22.
"""

from typing import Optional
import pandas as pd
from datetime import datetime

from app.broker.models import TradeSignal, TradeSide, SymbolSpecification, MarketRegime
from app.strategies.base import BaseStrategy


class TrendPullbackStrategy(BaseStrategy):
    """
    Identifies high-probability pullback entries in confirmed trending markets.
    """

    def __init__(self):
        super().__init__(name="TREND_PULLBACK")

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

        # Check regime: Must be trending or breakout
        if regime not in (MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN):
            return None

        curr = features_df.iloc[-1]
        prev = features_df.iloc[-2]

        close = curr["close"]
        high = curr["high"]
        low = curr["low"]
        ema_21 = curr["ema_21"]
        ema_50 = curr["ema_50"]
        ema_200 = curr["ema_200"]
        atr = max(curr["atr_14"], spec.tick_size * 10)
        adx = curr["adx"]

        # Check ADX trend strength
        if adx < 18.0:
            return None

        # Check higher timeframe alignment if available
        if higher_tf_features_df is not None and len(higher_tf_features_df) >= 10:
            htf_curr = higher_tf_features_df.iloc[-1]
            htf_aligned = (
                (htf_curr["ema_50"] > htf_curr["ema_200"])
                if regime == MarketRegime.TRENDING_UP
                else (htf_curr["ema_50"] < htf_curr["ema_200"])
            )
            if not htf_aligned:
                return None

        # ---------------- BULLISH SETUP ----------------
        if regime == MarketRegime.TRENDING_UP and ema_50 > ema_200:
            # Pullback criteria: Prior bar dipped near or below EMA21, current bar rejects and closes above
            dipped_to_pullback = prev["low"] <= ema_21 * 1.001
            structure_intact = close > curr["swing_low_level"]

            # Trigger criteria: Bullish rejection wick, engulfing, or close back above EMA21
            bullish_trigger = (
                (close > ema_21)
                and (close > prev["high"] or curr["is_bullish_rejection"] or curr["is_engulfing_bullish"])
            )

            if dipped_to_pullback and structure_intact and bullish_trigger:
                # Calculate Stop Loss: Below swing low or 1.5 ATR below entry
                sl_distance = max(1.5 * atr, (close - curr["swing_low_level"]) + atr * 0.2)
                stop_loss = round(close - sl_distance, spec.digits)
                # Take profit: 2.0x risk distance
                take_profit = round(close + (sl_distance * 2.0), spec.digits)

                return TradeSignal(
                    symbol=symbol,
                    side=TradeSide.BUY,
                    strategy=self.name,
                    timeframe="1m",
                    entry_price=close,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    timestamp=datetime.utcnow(),
                    metadata={
                        "adx": adx,
                        "atr": atr,
                        "sl_pips": sl_distance,
                        "rr": 2.0,
                    },
                )

        # ---------------- BEARISH SETUP ----------------
        elif regime == MarketRegime.TRENDING_DOWN and ema_50 < ema_200:
            # Pullback criteria: Prior bar rallied near or above EMA21, current bar rejects and closes below
            rallied_to_pullback = prev["high"] >= ema_21 * 0.999
            structure_intact = close < curr["swing_high_level"]

            # Trigger criteria: Bearish rejection wick, engulfing, or close back below EMA21
            bearish_trigger = (
                (close < ema_21)
                and (close < prev["low"] or curr["is_bearish_rejection"] or curr["is_engulfing_bearish"])
            )

            if rallied_to_pullback and structure_intact and bearish_trigger:
                sl_distance = max(1.5 * atr, (curr["swing_high_level"] - close) + atr * 0.2)
                stop_loss = round(close + sl_distance, spec.digits)
                take_profit = round(close - (sl_distance * 2.0), spec.digits)

                return TradeSignal(
                    symbol=symbol,
                    side=TradeSide.SELL,
                    strategy=self.name,
                    timeframe="1m",
                    entry_price=close,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    timestamp=datetime.utcnow(),
                    metadata={
                        "adx": adx,
                        "atr": atr,
                        "sl_pips": sl_distance,
                        "rr": 2.0,
                    },
                )

        return None
