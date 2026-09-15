"""
Fast Scalper Quantitative Scoring Engine.
Computes the multi-factor Scalp Score (0-100) combining tick velocity,
DOM imbalance, fast EMA 5/9/20 structure, spread filter, and relative volume.
(project.md Sections 1, 2, 3, 5, 7)
"""

from typing import Dict, Any, Optional, Tuple
import numpy as np
import pandas as pd

from app.broker.models import TradeSide, SymbolSpecification
from app.scalping.models import ScalpScore, ScalpTier, TickMetric, DOMQuote
from app.scalping.tick_engine import ScalpTickEngine


class FastScalper:
    """
    Tier-1 Fast Mathematical Scalping Evaluator.
    Screens candidates at ultra-low latency before dispatching
    high-conviction setups to the Deep Neural Network for confirmation.
    """

    def __init__(self, tick_engine: Optional[ScalpTickEngine] = None):
        self.tick_engine = tick_engine or ScalpTickEngine()

    def evaluate_symbol(
        self,
        symbol: str,
        df: pd.DataFrame,
        spec: Optional[SymbolSpecification] = None,
        tick_metric: Optional[TickMetric] = None,
        dom_quote: Optional[DOMQuote] = None,
    ) -> ScalpScore:
        """
        Calculates the complete 8-factor Scalp Score (0-100) per project.md specifications.
        """
        if df.empty or len(df) < 20:
            return self._create_empty_score(symbol)

        close = df["close"]
        high = df["high"]
        low = df["low"]
        vol = df["volume"] if "volume" in df else pd.Series(100.0, index=df.index)

        # -------------------------------------------------------------
        # 1. Spread Score (10%) - Rejects expensive spreads
        # -------------------------------------------------------------
        typical_atr = float((high - low).tail(14).mean())
        if tick_metric:
            spread_ratio = tick_metric.spread_ratio
        else:
            spread_ratio = 0.05  # Default tight

        # Ratio < 0.08 = 100pts, 0.15 = 70pts, > 0.30 = 0pts
        if spread_ratio <= 0.08:
            spread_score = 100.0
        elif spread_ratio <= 0.15:
            spread_score = 80.0
        elif spread_ratio <= 0.25:
            spread_score = 50.0
        else:
            spread_score = 15.0

        # -------------------------------------------------------------
        # 2. Fast EMA 5 / 9 / 20 Structure (10%)
        # -------------------------------------------------------------
        ema_5 = close.ewm(span=5, adjust=False).mean()
        ema_9 = close.ewm(span=9, adjust=False).mean()
        ema_20 = close.ewm(span=20, adjust=False).mean()

        curr_c = float(close.iloc[-1])
        c_ema5 = float(ema_5.iloc[-1])
        c_ema9 = float(ema_9.iloc[-1])
        c_ema20 = float(ema_20.iloc[-1])

        # Slopes over last 3 bars
        slope_5 = (c_ema5 - float(ema_5.iloc[-3])) / max(typical_atr, 1e-9)
        slope_9 = (c_ema9 - float(ema_9.iloc[-3])) / max(typical_atr, 1e-9)

        is_bull_ema = (c_ema5 > c_ema9 > c_ema20) and (curr_c >= c_ema5) and (slope_5 > 0)
        is_bear_ema = (c_ema5 < c_ema9 < c_ema20) and (curr_c <= c_ema5) and (slope_5 < 0)

        if is_bull_ema:
            ema_score = 100.0
            ema_align = "BULLISH"
            bias_dir = TradeSide.BUY
        elif is_bear_ema:
            ema_score = 100.0
            ema_align = "BEARISH"
            bias_dir = TradeSide.SELL
        else:
            # Partial alignment
            if c_ema5 > c_ema9:
                ema_score = 55.0
                ema_align = "WEAK_BULLISH"
                bias_dir = TradeSide.BUY
            elif c_ema5 < c_ema9:
                ema_score = 55.0
                ema_align = "WEAK_BEARISH"
                bias_dir = TradeSide.SELL
            else:
                ema_score = 30.0
                ema_align = "NEUTRAL"
                bias_dir = None

        # -------------------------------------------------------------
        # 3. Price Velocity (dp/dt) & Acceleration (15%)
        # -------------------------------------------------------------
        if tick_metric:
            vel = tick_metric.velocity_pts_sec
            accel = tick_metric.acceleration
        else:
            # Estimate from last 3 1m bars
            vel = float((close.iloc[-1] - close.iloc[-3]) / 180.0)
            accel = float((close.iloc[-1] - 2 * close.iloc[-2] + close.iloc[-3]) / 180.0)

        vel_normalized = abs(vel) / max(typical_atr * 0.05, 1e-9)
        velocity_score = float(np.clip(vel_normalized * 45.0, 10.0, 100.0))

        # Check velocity directional alignment
        if bias_dir == TradeSide.BUY and vel < 0:
            velocity_score *= 0.4
        elif bias_dir == TradeSide.SELL and vel > 0:
            velocity_score *= 0.4

        # -------------------------------------------------------------
        # 4. Tick Momentum (20%) - Acceleration trend (e.g. 61 -> 70 -> 82)
        # -------------------------------------------------------------
        # 3-bar rolling momentum
        m_curr = float(close.iloc[-1] - close.iloc[-2])
        m_prev = float(close.iloc[-2] - close.iloc[-3])
        m_prev2 = float(close.iloc[-3] - close.iloc[-4])

        is_accelerating = False
        if bias_dir == TradeSide.BUY:
            if m_curr > m_prev > m_prev2 and m_curr > 0:
                is_accelerating = True
                tick_mom_score = 95.0
            elif m_curr > 0:
                tick_mom_score = 75.0
            else:
                tick_mom_score = 25.0
        elif bias_dir == TradeSide.SELL:
            if m_curr < m_prev < m_prev2 and m_curr < 0:
                is_accelerating = True
                tick_mom_score = 95.0
            elif m_curr < 0:
                tick_mom_score = 75.0
            else:
                tick_mom_score = 25.0
        else:
            tick_mom_score = 45.0

        # -------------------------------------------------------------
        # 5. Relative Volume / Activity (15%)
        # -------------------------------------------------------------
        if tick_metric:
            rel_vol = tick_metric.relative_activity
        else:
            avg_vol = float(vol.tail(20).mean())
            curr_vol = float(vol.iloc[-1])
            rel_vol = curr_vol / max(avg_vol, 1.0)

        if rel_vol >= 2.0:
            activity_score = 100.0  # EXTREME
        elif rel_vol >= 1.5:
            activity_score = 85.0   # STRONG
        elif rel_vol >= 1.0:
            activity_score = 70.0   # ACTIVE
        elif rel_vol >= 0.7:
            activity_score = 50.0   # NORMAL
        else:
            activity_score = 20.0   # LOW ACTIVITY

        # -------------------------------------------------------------
        # 6. Depth of Market (DOM) Imbalance (15%)
        # -------------------------------------------------------------
        dom = dom_quote or self.tick_engine.get_dom_quote(symbol)
        dom_imb = dom.imbalance_ratio

        if bias_dir == TradeSide.BUY:
            # Buyer depth surplus (+0.2 to +1.0)
            if dom_imb >= 0.30:
                dom_score = 100.0
            elif dom_imb >= 0.10:
                dom_score = 78.0
            elif dom_imb >= -0.10:
                dom_score = 50.0
            else:
                dom_score = 20.0  # Selling wall against buy
        elif bias_dir == TradeSide.SELL:
            # Seller depth surplus (-0.2 to -1.0)
            if dom_imb <= -0.30:
                dom_score = 100.0
            elif dom_imb <= -0.10:
                dom_score = 78.0
            elif dom_imb <= 0.10:
                dom_score = 50.0
            else:
                dom_score = 20.0  # Buying wall against sell
        else:
            dom_score = 50.0

        # -------------------------------------------------------------
        # 7. ADX + DI Trend Strength (10%)
        # -------------------------------------------------------------
        # Estimate ADX/DI from candle ranges
        tr = np.maximum(high - low, np.maximum(abs(high - close.shift(1)), abs(low - close.shift(1))))
        atr_14 = tr.rolling(14).mean()
        up_move = high - high.shift(1)
        down_move = low.shift(1) - low

        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

        plus_di = 100.0 * pd.Series(plus_dm, index=df.index).rolling(14).mean() / atr_14.clip(lower=1e-9)
        minus_di = 100.0 * pd.Series(minus_dm, index=df.index).rolling(14).mean() / atr_14.clip(lower=1e-9)
        dx = 100.0 * abs(plus_di - minus_di) / (plus_di + minus_di).clip(lower=1e-9)
        adx = float(dx.rolling(14).mean().iloc[-1])

        c_plus = float(plus_di.iloc[-1])
        c_minus = float(minus_di.iloc[-1])

        if bias_dir == TradeSide.BUY and c_plus > c_minus and adx >= 25.0:
            adx_score = 95.0
        elif bias_dir == TradeSide.SELL and c_minus > c_plus and adx >= 25.0:
            adx_score = 95.0
        elif adx >= 20.0:
            adx_score = 65.0
        else:
            adx_score = 35.0

        # -------------------------------------------------------------
        # 8. ATR / Volatility Expansion (5%)
        # -------------------------------------------------------------
        recent_range = float((high.iloc[-1] - low.iloc[-1]))
        vol_ratio = recent_range / max(typical_atr, 1e-9)
        atr_score = float(np.clip(vol_ratio * 70.0, 20.0, 100.0))

        # -------------------------------------------------------------
        # COMPOSITE WEIGHTED SCALP SCORE (project.md Weights)
        # -------------------------------------------------------------
        composite = (
            (spread_score * 0.10)
            + (tick_mom_score * 0.20)
            + (velocity_score * 0.15)
            + (activity_score * 0.15)
            + (dom_score * 0.15)
            + (ema_score * 0.10)
            + (adx_score * 0.10)
            + (atr_score * 0.05)
        )
        total_score = round(float(np.clip(composite, 5.0, 99.0)), 1)

        # Classify Tier
        if total_score >= 85.0:
            tier = ScalpTier.HIGH_QUALITY
        elif total_score >= 75.0:
            tier = ScalpTier.GOOD
        elif total_score >= 65.0:
            tier = ScalpTier.WATCH
        elif total_score >= 50.0:
            tier = ScalpTier.WEAK
        else:
            tier = ScalpTier.NO_TRADE

        is_eligible = (total_score >= 75.0 and bias_dir is not None and spread_score >= 50.0)

        summary = (
            f"ScalpScore {total_score:.0f}/100 [{tier.value}] Dir: {bias_dir.value if bias_dir else 'NONE'} "
            f"(EMA: {ema_align}, Vel: {vel:.2f} pts/s, Act: {rel_vol:.1f}x, DOM: {dom_imb:+.2f}, Spread: {spread_score:.0f})"
        )

        return ScalpScore(
            symbol=symbol,
            total_score=total_score,
            tier=tier,
            direction=bias_dir,
            is_eligible=is_eligible,
            spread_score=round(spread_score, 1),
            tick_momentum_score=round(tick_mom_score, 1),
            velocity_score=round(velocity_score, 1),
            activity_score=round(activity_score, 1),
            dom_imbalance_score=round(dom_score, 1),
            ema_structure_score=round(ema_score, 1),
            adx_di_score=round(adx_score, 1),
            atr_volatility_score=round(atr_score, 1),
            raw_velocity=round(vel, 4),
            raw_activity_ratio=round(rel_vol, 2),
            raw_dom_imbalance=round(dom_imb, 3),
            raw_spread_points=round(tick_metric.spread_points if tick_metric else 0.0, 4),
            ema_alignment=ema_align,
            summary=summary,
        )

    def _create_empty_score(self, symbol: str) -> ScalpScore:
        return ScalpScore(
            symbol=symbol,
            total_score=30.0,
            tier=ScalpTier.NO_TRADE,
            direction=None,
            is_eligible=False,
            spread_score=50.0,
            tick_momentum_score=30.0,
            velocity_score=20.0,
            activity_score=20.0,
            dom_imbalance_score=50.0,
            ema_structure_score=30.0,
            adx_di_score=30.0,
            atr_volatility_score=30.0,
            raw_velocity=0.0,
            raw_activity_ratio=0.5,
            raw_dom_imbalance=0.0,
            raw_spread_points=0.0,
            ema_alignment="NONE",
            summary=f"Insufficient candle history for {symbol}",
        )
