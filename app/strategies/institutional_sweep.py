"""
Institutional Liquidity Sweep & Fair Value Gap (FVG) Strategy.
Trades smart-money liquidity hunts and imbalance mitigations.
"""

from typing import Optional
from datetime import datetime
import pandas as pd

from app.broker.models import TradeSignal, TradeSide, SymbolSpecification, MarketRegime
from app.strategies.base import BaseStrategy


class InstitutionalLiquiditySweepStrategy(BaseStrategy):
    """
    Executes institutional fades on liquidity sweeps and FVG retests.
    """

    def __init__(self):
        super().__init__(name="INSTITUTIONAL_SWEEP")

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
        high = curr["high"]
        low = curr["low"]
        atr = max(curr.get("atr_14", 1.0), spec.tick_size * 10)

        # ---------------- BULLISH LIQUIDITY SWEEP / FVG RETEST ----------------
        # 1. Sweep of Session Low
        has_low_sweep = curr.get("sweep_session_low", 0) == 1 or curr.get("liquidity_sweep_low", 0) == 1
        # 2. Bullish FVG mitigation
        in_bull_fvg = curr.get("in_bullish_fvg", 0) == 1 and curr.get("is_bullish_rejection", 0) == 1

        if has_low_sweep or in_bull_fvg:
            # Stop loss strictly below the sweep low + small buffer
            sl_distance = max(1.2 * atr, (close - low) + atr * 0.2)
            stop_loss = round(close - sl_distance, spec.digits)
            # Target Point of Control or 2.5x R:R
            target_distance = sl_distance * 2.5
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
                metadata={
                    "setup": "BULLISH_SWEEP" if has_low_sweep else "FVG_MITIGATION",
                    "rr": 2.5,
                },
            )

        # ---------------- BEARISH LIQUIDITY SWEEP / FVG RETEST ----------------
        has_high_sweep = curr.get("sweep_session_high", 0) == 1 or curr.get("liquidity_sweep_high", 0) == 1
        in_bear_fvg = curr.get("in_bearish_fvg", 0) == 1 and curr.get("is_bearish_rejection", 0) == 1

        if has_high_sweep or in_bear_fvg:
            sl_distance = max(1.2 * atr, (high - close) + atr * 0.2)
            stop_loss = round(close + sl_distance, spec.digits)
            target_distance = sl_distance * 2.5
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
                metadata={
                    "setup": "BEARISH_SWEEP" if has_high_sweep else "FVG_MITIGATION",
                    "rr": 2.5,
                },
            )

        return None
