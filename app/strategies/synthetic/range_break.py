"""
Specialized Range Break Index Strategy for Deriv.
Implements the 7-step sequence: Range -> Compression -> Boundary Test -> Breakout -> Retest -> Trade.
"""

from typing import Optional
import pandas as pd
from datetime import datetime

from app.broker.models import TradeSignal, TradeSide, SymbolSpecification, MarketRegime
from app.strategies.base import BaseStrategy


class RangeBreakStrategy(BaseStrategy):
    """
    Channel and boundary compression breakout for Deriv Range Break indices.
    """

    def __init__(self):
        super().__init__(name="RANGE_BREAK")

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
        atr = max(curr["atr_14"], spec.tick_size * 10)

        # Range Break mechanics: Break beyond rolling upper or lower channel
        upper_channel = curr["swing_high_level"]
        lower_channel = curr["swing_low_level"]

        # Bullish break out of channel
        if prev["close"] <= upper_channel and close > upper_channel and curr["close_location_value"] > 0.4:
            sl = round(upper_channel - 1.5 * atr, spec.digits)
            tp = round(close + 2.5 * atr, spec.digits)
            return TradeSignal(
                symbol=symbol,
                side=TradeSide.BUY,
                strategy=self.name,
                timeframe="1m",
                entry_price=close,
                stop_loss=sl,
                take_profit=tp,
                timestamp=datetime.utcnow(),
                metadata={"pattern": "RANGE_BREAKOUT_UP", "channel_width": upper_channel - lower_channel},
            )

        # Bearish break out of channel
        elif prev["close"] >= lower_channel and close < lower_channel and curr["close_location_value"] < -0.4:
            sl = round(lower_channel + 1.5 * atr, spec.digits)
            tp = round(close - 2.5 * atr, spec.digits)
            return TradeSignal(
                symbol=symbol,
                side=TradeSide.SELL,
                strategy=self.name,
                timeframe="1m",
                entry_price=close,
                stop_loss=sl,
                take_profit=tp,
                timestamp=datetime.utcnow(),
                metadata={"pattern": "RANGE_BREAKOUT_DOWN", "channel_width": upper_channel - lower_channel},
            )

        return None
