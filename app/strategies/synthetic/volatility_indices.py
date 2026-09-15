"""
Specialized Strategies for Deriv 1-Second Volatility Indices (Vol 15, 30, 90).
Tailored to the specific statistical profiles detailed in strategy.md Section 8 & 21.
"""

from typing import Optional
import pandas as pd
from datetime import datetime

from app.broker.models import TradeSignal, TradeSide, SymbolSpecification, MarketRegime
from app.strategies.base import BaseStrategy


class DerivVolatilityStrategy(BaseStrategy):
    """
    Adaptive strategy tailored for Deriv Volatility Indices.
    """

    def __init__(self):
        super().__init__(name="DERIV_VOLATILITY")

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
        close = curr["close"]
        atr = max(curr["atr_14"], spec.tick_size * 5)
        adx = curr["adx"]
        sym_lower = symbol.lower()

        # ---------------- Volatility 15 (1s): Low-Vol Scalping / Mean Reversion ----------------
        if "15" in sym_lower:
            if regime in (MarketRegime.RANGING, MarketRegime.LOW_VOLATILITY):
                if curr["rsi_14"] < 35 and curr["is_bullish_rejection"]:
                    sl = round(close - 1.2 * atr, spec.digits)
                    tp = round(close + 1.8 * atr, spec.digits)
                    return TradeSignal(
                        symbol=symbol,
                        side=TradeSide.BUY,
                        strategy="VOL_15_SCALP",
                        timeframe="1m",
                        entry_price=close,
                        stop_loss=sl,
                        take_profit=tp,
                        timestamp=datetime.utcnow(),
                    )
                elif curr["rsi_14"] > 65 and curr["is_bearish_rejection"]:
                    sl = round(close + 1.2 * atr, spec.digits)
                    tp = round(close - 1.8 * atr, spec.digits)
                    return TradeSignal(
                        symbol=symbol,
                        side=TradeSide.SELL,
                        strategy="VOL_15_SCALP",
                        timeframe="1m",
                        entry_price=close,
                        stop_loss=sl,
                        take_profit=tp,
                        timestamp=datetime.utcnow(),
                    )

        # ---------------- Volatility 30 (1s): Momentum / Range Rotation ----------------
        elif "30" in sym_lower:
            if adx > 22.0:
                if curr["plus_di"] > curr["minus_di"] and curr["return_3"] > 0:
                    sl = round(close - 1.5 * atr, spec.digits)
                    tp = round(close + 2.2 * atr, spec.digits)
                    return TradeSignal(
                        symbol=symbol,
                        side=TradeSide.BUY,
                        strategy="VOL_30_MOMENTUM",
                        timeframe="1m",
                        entry_price=close,
                        stop_loss=sl,
                        take_profit=tp,
                        timestamp=datetime.utcnow(),
                    )
                elif curr["minus_di"] > curr["plus_di"] and curr["return_3"] < 0:
                    sl = round(close + 1.5 * atr, spec.digits)
                    tp = round(close - 2.2 * atr, spec.digits)
                    return TradeSignal(
                        symbol=symbol,
                        side=TradeSide.SELL,
                        strategy="VOL_30_MOMENTUM",
                        timeframe="1m",
                        entry_price=close,
                        stop_loss=sl,
                        take_profit=tp,
                        timestamp=datetime.utcnow(),
                    )

        # ---------------- Volatility 90 (1s): Breakout / High Risk Expansion ----------------
        elif "90" in sym_lower or "100" in sym_lower or "75" in sym_lower:
            if curr["volatility_expansion_ratio"] > 1.25 and curr["adx"] > 25.0:
                if curr["close_location_value"] > 0.5:
                    sl = round(close - 2.0 * atr, spec.digits)
                    tp = round(close + 3.0 * atr, spec.digits)
                    return TradeSignal(
                        symbol=symbol,
                        side=TradeSide.BUY,
                        strategy="VOL_HIGH_BREAKOUT",
                        timeframe="1m",
                        entry_price=close,
                        stop_loss=sl,
                        take_profit=tp,
                        timestamp=datetime.utcnow(),
                    )
                elif curr["close_location_value"] < -0.5:
                    sl = round(close + 2.0 * atr, spec.digits)
                    tp = round(close - 3.0 * atr, spec.digits)
                    return TradeSignal(
                        symbol=symbol,
                        side=TradeSide.SELL,
                        strategy="VOL_HIGH_BREAKOUT",
                        timeframe="1m",
                        entry_price=close,
                        stop_loss=sl,
                        take_profit=tp,
                        timestamp=datetime.utcnow(),
                    )

        return None
