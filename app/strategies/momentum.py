"""
Strategy #3: Momentum Continuation Strategy.
Captures high-velocity directional runs when ADX > 25 and ATR expands.
"""

from typing import Optional
import pandas as pd
from datetime import datetime

from app.broker.models import TradeSignal, TradeSide, SymbolSpecification, MarketRegime
from app.strategies.base import BaseStrategy


class MomentumStrategy(BaseStrategy):
    """
    Momentum continuation strategy for fast-moving markets.
    """

    def __init__(self):
        super().__init__(name="MOMENTUM")

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
        adx = curr["adx"]
        atr = max(curr["atr_14"], spec.tick_size * 10)
        plus_di = curr["plus_di"]
        minus_di = curr["minus_di"]
        ema_aligned = curr["ema_trend_aligned"]

        # Strong momentum requirement
        if adx < 25.0:
            return None

        # ---------------- BULLISH MOMENTUM ----------------
        if plus_di > minus_di + 10 and ema_aligned == 1 and curr["return_3"] > 0:
            if curr["close_location_value"] > 0.4 and curr["body_ratio"] > 0.45:
                sl_distance = max(1.2 * atr, spec.tick_size * 20)
                stop_loss = round(close - sl_distance, spec.digits)
                take_profit = round(close + (sl_distance * 1.8), spec.digits)

                return TradeSignal(
                    symbol=symbol,
                    side=TradeSide.BUY,
                    strategy=self.name,
                    timeframe="1m",
                    entry_price=close,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    timestamp=datetime.utcnow(),
                    metadata={"adx": adx, "rr": 1.8},
                )

        # ---------------- BEARISH MOMENTUM ----------------
        elif minus_di > plus_di + 10 and ema_aligned == -1 and curr["return_3"] < 0:
            if curr["close_location_value"] < -0.4 and curr["body_ratio"] > 0.45:
                sl_distance = max(1.2 * atr, spec.tick_size * 20)
                stop_loss = round(close + sl_distance, spec.digits)
                take_profit = round(close - (sl_distance * 1.8), spec.digits)

                return TradeSignal(
                    symbol=symbol,
                    side=TradeSide.SELL,
                    strategy=self.name,
                    timeframe="1m",
                    entry_price=close,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    timestamp=datetime.utcnow(),
                    metadata={"adx": adx, "rr": 1.8},
                )

        return None
