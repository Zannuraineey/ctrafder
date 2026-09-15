"""
Statistical Event Strategy for Deriv Crash and Boom Indices.
Accounts for non-linear asymmetric spike behavior.
"""

from typing import Optional
import pandas as pd
from datetime import datetime

from app.broker.models import TradeSignal, TradeSide, SymbolSpecification, MarketRegime
from app.strategies.base import BaseStrategy


class CrashBoomStrategy(BaseStrategy):
    """
    Event-specific strategy for Crash/Boom indices.
    Exploits post-spike stabilization and strictly avoids holding against spikes.
    """

    def __init__(self):
        super().__init__(name="CRASH_BOOM_STATISTICAL")

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
        close = curr["close"]
        sym_lower = symbol.lower()
        atr = max(curr["atr_14"], spec.tick_size * 10)

        # ---------------- CRASH INDICES (Spike DOWN, gradual rise) ----------------
        if "crash" in sym_lower:
            # Post-crash recovery setup: Huge down candle occurred 2-3 bars ago, market now stabilizing
            recent_candles = features_df.iloc[-5:-1]
            had_recent_crash = (recent_candles["return_1"] < -0.015).any()

            # If crash just happened and current candle closes bullish with lower wick rejection
            if had_recent_crash and curr["is_bullish_rejection"] and curr["close"] > prev["close"]:
                sl = round(curr["low"] - atr * 0.5, spec.digits)
                tp = round(close + atr * 2.0, spec.digits)
                return TradeSignal(
                    symbol=symbol,
                    side=TradeSide.BUY,
                    strategy="CRASH_RECOVERY",
                    timeframe="1m",
                    entry_price=close,
                    stop_loss=sl,
                    take_profit=tp,
                    timestamp=datetime.utcnow(),
                    metadata={"target": "QUICK_RECOVERY_SCALP"},
                )

        # ---------------- BOOM INDICES (Spike UP, gradual decline) ----------------
        elif "boom" in sym_lower:
            recent_candles = features_df.iloc[-5:-1]
            had_recent_boom = (recent_candles["return_1"] > 0.015).any()

            if had_recent_boom and curr["is_bearish_rejection"] and curr["close"] < prev["close"]:
                sl = round(curr["high"] + atr * 0.5, spec.digits)
                tp = round(close - atr * 2.0, spec.digits)
                return TradeSignal(
                    symbol=symbol,
                    side=TradeSide.SELL,
                    strategy="BOOM_RECOVERY",
                    timeframe="1m",
                    entry_price=close,
                    stop_loss=sl,
                    take_profit=tp,
                    timestamp=datetime.utcnow(),
                    metadata={"target": "QUICK_RECOVERY_SCALP"},
                )

        return None
