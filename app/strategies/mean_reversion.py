"""
Strategy #4: Range Mean Reversion Strategy.
Active strictly in RANGING or LOW_VOLATILITY regimes.
Enforces the safety rule: strictly disabled during strong trends.
"""

from typing import Optional
import pandas as pd
from datetime import datetime

from app.broker.models import TradeSignal, TradeSide, SymbolSpecification, MarketRegime
from app.strategies.base import BaseStrategy


class MeanReversionStrategy(BaseStrategy):
    """
    Mean reversion oscillator strategy active strictly inside ranges.
    """

    def __init__(self):
        super().__init__(name="MEAN_REVERSION")

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

        # STRICT SAFETY RULE: Only active in confirmed range
        if regime not in (MarketRegime.RANGING, MarketRegime.LOW_VOLATILITY):
            return None

        curr = features_df.iloc[-1]
        prev = features_df.iloc[-2]

        adx = curr["adx"]
        # If trend momentum is elevated, disable mean reversion to prevent counter-trend stopouts
        if adx > 22.0:
            return None

        close = curr["close"]
        rsi = curr["rsi_14"]
        bb_percent_b = curr["bb_percent_b"]
        atr = max(curr["atr_14"], spec.tick_size * 10)

        # ---------------- OVERSOLD BOUNCE (BUY) ----------------
        if rsi < 32.0 and bb_percent_b < 0.05 and curr["is_bullish_rejection"]:
            sl_distance = max(1.2 * atr, (close - curr["low"]) + atr * 0.5)
            stop_loss = round(close - sl_distance, spec.digits)
            # Target is the middle Bollinger Band
            target_distance = max(sl_distance * 1.5, curr["bb_middle"] - close)
            take_profit = round(close + target_distance, spec.digits)

            return TradeSignal(
                symbol=symbol,
                side=TradeSide.BUY,
                strategy=self.name,
                timeframe="1m",
                entry_price=close,
                stop_loss=stop_loss,
                take_profit=take_profit,
                timestamp=datetime.utcnow(),
                metadata={"rsi": rsi, "rr": round(target_distance / sl_distance, 2)},
            )

        # ---------------- OVERBOUGHT REJECTION (SELL) ----------------
        elif rsi > 68.0 and bb_percent_b > 0.95 and curr["is_bearish_rejection"]:
            sl_distance = max(1.2 * atr, (curr["high"] - close) + atr * 0.5)
            stop_loss = round(close + sl_distance, spec.digits)
            target_distance = max(sl_distance * 1.5, close - curr["bb_middle"])
            take_profit = round(close - target_distance, spec.digits)

            return TradeSignal(
                symbol=symbol,
                side=TradeSide.SELL,
                strategy=self.name,
                timeframe="1m",
                entry_price=close,
                stop_loss=stop_loss,
                take_profit=take_profit,
                timestamp=datetime.utcnow(),
                metadata={"rsi": rsi, "rr": round(target_distance / sl_distance, 2)},
            )

        return None
