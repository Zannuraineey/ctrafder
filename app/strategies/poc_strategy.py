"""
Point of Control (POC) Reaction & Volume Profile Strategy.
Identifies institutional high-volume price acceptance/rejection nodes,
and trades candle bounces off POC support, rejections off POC resistance,
and Value Area mean-reversion magnet setups.
"""

from typing import Optional, Dict, Any, Tuple, List
from datetime import datetime
import numpy as np
import pandas as pd
from loguru import logger

from app.broker.models import TradeSignal, TradeSide, SymbolSpecification, MarketRegime
from app.strategies.base import BaseStrategy


def compute_volume_profile(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    volumes: np.ndarray,
    digits: int = 5,
    num_bins: int = 24,
) -> Tuple[float, float, float]:
    """
    Computes Point of Control (POC), Value Area High (VAH), and Value Area Low (VAL)
    from candle arrays with full NaN / Inf safety.
    """
    if len(closes) == 0:
        return 0.0, 0.0, 0.0

    highs = np.nan_to_num(highs, nan=0.0)
    lows = np.nan_to_num(lows, nan=0.0)
    closes = np.nan_to_num(closes, nan=0.0)
    volumes = np.nan_to_num(volumes, nan=1.0)

    min_p = float(np.min(lows))
    max_p = float(np.max(highs))
    if max_p <= min_p or not np.isfinite(min_p) or not np.isfinite(max_p):
        last_c = float(closes[-1]) if len(closes) > 0 and np.isfinite(closes[-1]) else 0.0
        c = round(last_c, digits)
        return c, c, c

    bins = np.linspace(min_p, max_p, num_bins + 1)
    bin_vols = np.zeros(num_bins)

    for h, l, c, v in zip(highs, lows, closes, volumes):
        vol = max(float(v), 1.0)
        low_idx = int(np.clip(np.digitize(l, bins) - 1, 0, num_bins - 1))
        high_idx = int(np.clip(np.digitize(h, bins) - 1, 0, num_bins - 1))
        if low_idx == high_idx:
            bin_vols[low_idx] += vol
        else:
            span = max(high_idx - low_idx + 1, 1)
            portion = vol / span
            bin_vols[low_idx : high_idx + 1] += portion

    poc_idx = int(np.argmax(bin_vols))
    poc_raw = (bins[poc_idx] + bins[poc_idx + 1]) / 2.0
    poc_price = round(float(poc_raw) if np.isfinite(poc_raw) else min_p, digits)

    # 70% Value Area surrounding POC
    total_vol = max(float(np.sum(bin_vols)), 1.0)
    target_vol = total_vol * 0.70
    curr_vol = float(bin_vols[poc_idx])
    left_idx = poc_idx
    right_idx = poc_idx

    while curr_vol < target_vol and (left_idx > 0 or right_idx < num_bins - 1):
        left_v = bin_vols[left_idx - 1] if left_idx > 0 else 0.0
        right_v = bin_vols[right_idx + 1] if right_idx < num_bins - 1 else 0.0
        if left_v >= right_v and left_idx > 0:
            left_idx -= 1
            curr_vol += left_v
        elif right_idx < num_bins - 1:
            right_idx += 1
            curr_vol += right_v
        else:
            break

    val_raw = bins[left_idx]
    vah_raw = bins[right_idx + 1]
    val = round(float(val_raw) if np.isfinite(val_raw) else min_p, digits)
    vah = round(float(vah_raw) if np.isfinite(vah_raw) else max_p, digits)
    return poc_price, vah, val


class POCReactionStrategy(BaseStrategy):
    """
    Executes institutional setups anchored to Point of Control (POC):
    1. Bullish POC Support Bounce (retesting high-volume node from above).
    2. Bearish POC Resistance Rejection (retesting high-volume node from below).
    3. Value Area Extremum Reversion (reverting to POC magnet from VAL or VAH).
    """

    def __init__(self):
        super().__init__(name="POC_REACTION")

    def evaluate(
        self,
        symbol: str,
        features_df: pd.DataFrame,
        regime: MarketRegime,
        spec: SymbolSpecification,
        higher_tf_features_df: Optional[pd.DataFrame] = None,
    ) -> Optional[TradeSignal]:
        if len(features_df) < 15:
            return None

        # Look back up to 50 candles for the active volume profile
        lookback = min(len(features_df), 50)
        recent = features_df.iloc[-lookback:]

        highs = recent["high"].to_numpy()
        lows = recent["low"].to_numpy()
        closes = recent["close"].to_numpy()
        volumes = (
            recent["volume"].to_numpy()
            if "volume" in recent
            else np.ones(len(recent)) * 100.0
        )

        poc_price, vah, val = compute_volume_profile(
            highs, lows, closes, volumes, digits=spec.digits
        )

        curr = features_df.iloc[-1]
        prev = features_df.iloc[-2]

        curr_close = float(curr["close"])
        curr_open = float(curr.get("open", prev["close"]))
        curr_high = float(curr["high"])
        curr_low = float(curr["low"])

        # Check the last 3 candles to detect if price reached or tested POC recently
        recent_window = features_df.iloc[-3:] if len(features_df) >= 3 else features_df
        min_recent_low = float(recent_window["low"].min())
        max_recent_high = float(recent_window["high"].max())

        atr = float(curr.get("atr_14", max(0.0005, curr_close * 0.001)))
        tolerance = max(atr * 0.65, spec.tick_size * 8)

        is_bullish_reaction = (curr_close > curr_open) or ((curr_close - curr_low) > (curr_high - curr_close) * 1.2)
        is_bearish_reaction = (curr_close < curr_open) or ((curr_high - curr_close) > (curr_close - curr_low) * 1.2)

        # 1. BULLISH POC SUPPORT BOUNCE
        # Price reached / tested POC support within the recent window and bounced bullishly
        tested_poc_support = (min_recent_low <= poc_price + tolerance) and (curr_close >= poc_price - (atr * 0.25))

        if tested_poc_support and is_bullish_reaction and not (curr_close < curr_open and curr_close < float(prev["close"])):
            # Stop loss strictly below POC and recent low with safety buffer
            sl_dist = max(atr * 1.2, (curr_close - min(poc_price, min_recent_low)) + atr * 0.3)
            stop_loss = round(curr_close - sl_dist, spec.digits)
            # High reward target: targeting VAH or minimum 2.5R
            tp_dist = max(sl_dist * 2.8, (vah - curr_close) * 1.2)
            take_profit = round(curr_close + tp_dist, spec.digits)

            return TradeSignal(
                symbol=symbol,
                side=TradeSide.BUY,
                strategy=self.name,
                timeframe="1m",
                entry_price=curr_close,
                stop_loss=stop_loss,
                take_profit=take_profit,
                timestamp=datetime.utcnow(),
                metadata={
                    "setup": "POC_SUPPORT_BOUNCE",
                    "poc": poc_price,
                    "vah": vah,
                    "val": val,
                    "rr": round(tp_dist / max(sl_dist, 1e-9), 2),
                },
            )

        # 2. BEARISH POC RESISTANCE REJECTION
        # Price reached / tested POC resistance within the recent window and rejected bearishly
        tested_poc_resistance = (max_recent_high >= poc_price - tolerance) and (curr_close <= poc_price + (atr * 0.25))

        if tested_poc_resistance and is_bearish_reaction and not (curr_close > curr_open and curr_close > float(prev["close"])):
            # Stop loss strictly above POC and recent high with safety buffer
            sl_dist = max(atr * 1.2, (max(poc_price, max_recent_high) - curr_close) + atr * 0.3)
            stop_loss = round(curr_close + sl_dist, spec.digits)
            # High reward target: targeting VAL or minimum 2.5R
            tp_dist = max(sl_dist * 2.8, (curr_close - val) * 1.2)
            take_profit = round(curr_close - tp_dist, spec.digits)

            return TradeSignal(
                symbol=symbol,
                side=TradeSide.SELL,
                strategy=self.name,
                timeframe="1m",
                entry_price=curr_close,
                stop_loss=stop_loss,
                take_profit=take_profit,
                timestamp=datetime.utcnow(),
                metadata={
                    "setup": "POC_RESISTANCE_REJECTION",
                    "poc": poc_price,
                    "vah": vah,
                    "val": val,
                    "rr": round(tp_dist / max(sl_dist, 1e-9), 2),
                },
            )

        # 3. VALUE AREA EXTREMUM MAGNET REVERSION
        # Price pushed below VAL, rejected continuation -> buy targeting POC
        if curr_low < val - (atr * 0.25) and curr_close > curr_low + (atr * 0.15):
            sl_dist = max(atr * 1.1, (curr_close - curr_low) + atr * 0.2)
            stop_loss = round(curr_close - sl_dist, spec.digits)
            take_profit = round(poc_price + (atr * 0.5), spec.digits)
            if take_profit > curr_close + (sl_dist * 1.8):
                return TradeSignal(
                    symbol=symbol,
                    side=TradeSide.BUY,
                    strategy=self.name,
                    timeframe="1m",
                    entry_price=curr_close,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    timestamp=datetime.utcnow(),
                    metadata={
                        "setup": "VAL_MAGNET_REVERSION",
                        "poc": poc_price,
                        "vah": vah,
                        "val": val,
                        "rr": round((take_profit - curr_close) / max(sl_dist, 1e-9), 2),
                    },
                )

        # Price pushed above VAH, rejected continuation -> sell targeting POC
        if curr_high > vah + (atr * 0.25) and curr_close < curr_high - (atr * 0.15):
            sl_dist = max(atr * 1.1, (curr_high - curr_close) + atr * 0.2)
            stop_loss = round(curr_close + sl_dist, spec.digits)
            take_profit = round(poc_price - (atr * 0.5), spec.digits)
            if take_profit < curr_close - (sl_dist * 1.8):
                return TradeSignal(
                    symbol=symbol,
                    side=TradeSide.SELL,
                    strategy=self.name,
                    timeframe="1m",
                    entry_price=curr_close,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    timestamp=datetime.utcnow(),
                    metadata={
                        "setup": "VAH_MAGNET_REVERSION",
                        "poc": poc_price,
                        "vah": vah,
                        "val": val,
                        "rr": round((curr_close - take_profit) / max(sl_dist, 1e-9), 2),
                    },
                )

        return None
