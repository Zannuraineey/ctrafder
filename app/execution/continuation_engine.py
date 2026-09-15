"""
Continuation Engine and Trade Lifecycle Manager.
Determines whether an active trade or setup has sufficient institutional fuel to continue,
and outputs intelligent lifecycle management directives: ENTER, HOLD, PROTECT, or EXIT.
(project.md Sections 3, 4, 6, 7; strategy.md)
"""

from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import numpy as np

from app.market.volume_pressure import VolumePressureEngine, VolumeState, VolumePressureMetrics
from app.market.momentum_engine import AdvancedMomentumEngine, MomentumState, MomentumTier, MomentumMetrics
from app.broker.models import TradeSide, Position


class LifecycleAction(str, Enum):
    ENTER = "ENTER"                    # Setup has strong continuation probability (>= 0.65)
    HOLD = "HOLD"                      # MOMENTUM_HOLD: Strong fuel & structure; let profits run
    PROFIT_EXTENSION = "PROFIT_EXTENSION" # In profit with healthy continuation (>= 55%); extend gains
    PROTECT = "PROTECT"                # PROFIT_PROTECTION: Auto-BE active / trailing stop protecting profit
    MOMENTUM_DECAY = "MOMENTUM_DECAY"  # Momentum fading/weakening; trail tighter
    EXHAUSTION_EXIT = "EXHAUSTION_EXIT" # Real volume exhaustion + momentum reversal -> Lock in profits now
    STRUCTURE_EXIT = "STRUCTURE_EXIT"  # Market structure broken (lower low on buy or higher high on sell)
    EXIT = "EXIT"                      # Emergency exit: severe momentum failure or reverse
    SCALP_TAKE = "SCALP_TAKE"          # Retain for backward compatibility


@dataclass
class ContinuationEvaluation:
    continuation_probability: float  # 0.0 to 1.0
    continuation_score: float        # 0 to 100
    lifecycle_action: LifecycleAction
    momentum_metrics: MomentumMetrics
    volume_metrics: VolumePressureMetrics
    is_structure_intact: bool
    is_exhaustion_detected: bool
    reasoning: str


class ContinuationEngine:
    """
    Synthesizes Market Structure, Momentum Engine, Volume Pressure, and Volatility
    to evaluate ongoing trade viability and answer:
    'Does this move still have fuel to continue?'
    """

    @classmethod
    def evaluate_setup(
        cls,
        df: pd.DataFrame,
        side: TradeSide,
    ) -> ContinuationEvaluation:
        """
        Evaluates a prospective trade entry setup before execution.
        """
        is_bull = (side == TradeSide.BUY)
        mom = AdvancedMomentumEngine.analyze(df, is_bullish_bias=is_bull)
        vol = VolumePressureEngine.analyze(df)

        # Structure check: higher highs/lows for buy, lower highs/lows for sell
        is_structure_intact = cls._check_market_structure(df, is_bull)

        # Continuation Score calculation
        # 40% Momentum Score + 35% Volume Participation + 15% Structure + 10% Directional Confirmation
        struct_pts = 15.0 if is_structure_intact else 0.0
        conf_pts = 10.0 if vol.is_confirming_direction else 0.0
        raw_score = (mom.momentum_score * 0.40) + (vol.participation_score * 0.35) + struct_pts + conf_pts

        if vol.is_exhaustion_detected:
            raw_score -= 25.0

        continuation_score = float(np.clip(raw_score, 5.0, 99.0))
        continuation_prob = round(continuation_score / 100.0, 2)

        # Action determination for new setup
        if continuation_prob >= 0.65 and not vol.is_exhaustion_detected and is_structure_intact:
            action = LifecycleAction.ENTER
            reasoning = (
                f"Sufficient continuation fuel ({continuation_score:.0f}/100). "
                f"Mom: {mom.momentum_score}, Vol: {vol.participation_score}, Structure: INTACT."
            )
        else:
            action = LifecycleAction.EXIT  # In setup context, this means Do Not Enter
            reasoning = (
                f"Insufficient fuel ({continuation_score:.0f}/100). "
                f"Mom: {mom.momentum_score}, Vol: {vol.participation_score}, Exhaustion: {vol.is_exhaustion_detected}"
            )

        return ContinuationEvaluation(
            continuation_probability=continuation_prob,
            continuation_score=continuation_score,
            lifecycle_action=action,
            momentum_metrics=mom,
            volume_metrics=vol,
            is_structure_intact=is_structure_intact,
            is_exhaustion_detected=vol.is_exhaustion_detected,
            reasoning=reasoning,
        )

    @classmethod
    def evaluate_active_position(
        cls,
        position: Position,
        df: pd.DataFrame,
        trading_mode: str = "NORMAL",
    ) -> ContinuationEvaluation:
        """
        Evaluates an active open position in real time to decide HOLD, PROTECT, or EXIT.
        Supports execution profiles:
        - NORMAL: Swing / momentum hold, trend continuation, profit extension.
        - SCALPING: Fast impulse entries, rapid profit snatch ($0.25-$0.50+), immediate exit on momentum fail.
        - ADAPTIVE: Dynamically chooses between scalping impulse or trend holding based on regime.
        """
        is_bull = (position.side == TradeSide.BUY)
        mom = AdvancedMomentumEngine.analyze(df, is_bullish_bias=is_bull)
        vol = VolumePressureEngine.analyze(df)
        is_struct_intact = cls._check_market_structure(df, is_bull)

        # Base continuation score
        struct_pts = 20.0 if is_struct_intact else 0.0
        conf_pts = 10.0 if vol.is_confirming_direction else 0.0
        raw_score = (mom.momentum_score * 0.40) + (vol.participation_score * 0.30) + struct_pts + conf_pts

        if vol.is_exhaustion_detected:
            raw_score -= 30.0

        # Adjust for position profitability
        # If in profit, reward positive momentum
        pnl = position.unrealized_pnl
        if pnl > 0 and mom.momentum_score >= 65.0:
            raw_score += 5.0

        continuation_score = float(np.clip(raw_score, 2.0, 99.0))
        continuation_prob = round(continuation_score / 100.0, 2)

        # ======================================================================
        # SCALPING EXECUTION PROFILE (project.md Scalping Architecture)
        # Fast entries / fast micro exits: Snatch quick profit or cut immediately when momentum fails
        # ======================================================================
        effective_mode = trading_mode.upper() if trading_mode else "NORMAL"
        if effective_mode == "ADAPTIVE":
            effective_mode = "SCALPING" if (mom.momentum_score >= 60.0 or vol.participation_score >= 60.0) else "NORMAL"

        if effective_mode == "SCALPING":
            # 1. Profit Target Reached: Take profit immediately!
            # - Flat exit if profit >= $0.50
            # - Fast exit if profit >= $0.25 and momentum cooling or exhaustion detected
            if pnl >= 0.50:
                return ContinuationEvaluation(
                    continuation_probability=continuation_prob,
                    continuation_score=continuation_score,
                    lifecycle_action=LifecycleAction.SCALP_TAKE,
                    momentum_metrics=mom,
                    volume_metrics=vol,
                    is_structure_intact=is_struct_intact,
                    is_exhaustion_detected=vol.is_exhaustion_detected,
                    reasoning=f"⚡ [SCALPING PROFIT SNATCH] Reached +${pnl:.2f} -> Immediate Scalp Exit to lock in profit!"
                )

            if pnl >= 0.25 and (mom.momentum_score < 55.0 or vol.is_exhaustion_detected or mom.state in (MomentumState.WEAKENING, MomentumState.PEAK, MomentumState.FAILED)):
                return ContinuationEvaluation(
                    continuation_probability=continuation_prob,
                    continuation_score=continuation_score,
                    lifecycle_action=LifecycleAction.SCALP_TAKE,
                    momentum_metrics=mom,
                    volume_metrics=vol,
                    is_structure_intact=is_struct_intact,
                    is_exhaustion_detected=True,
                    reasoning=f"⚡ [SCALPING PROFIT SNATCH] Banked +${pnl:.2f} as momentum cooled ({mom.momentum_score:.0f}/100) -> Lock in profit before giveback!"
                )

            # 2. Scalping Momentum Fails -> EXIT IMMEDIATELY (project.md: 'MOMENTUM FAILS? YES -> EXIT')
            if mom.momentum_score < 30.0 or mom.state in (MomentumState.FAILED, MomentumState.REVERSED):
                return ContinuationEvaluation(
                    continuation_probability=continuation_prob,
                    continuation_score=continuation_score,
                    lifecycle_action=LifecycleAction.EXIT,
                    momentum_metrics=mom,
                    volume_metrics=vol,
                    is_structure_intact=is_struct_intact,
                    is_exhaustion_detected=vol.is_exhaustion_detected,
                    reasoning=f"⚠️ [SCALPING MOMENTUM FAIL] Momentum collapsed to {mom.momentum_score:.0f}/100 ({mom.state.value}) -> Fast Exit"
                )

            # 3. If in micro-profit, protect with BE-SECURE while momentum is still accelerating
            if pnl >= 0.20:
                if mom.momentum_score >= 60.0 and mom.state == MomentumState.ACCELERATING and is_struct_intact:
                    action = LifecycleAction.PROFIT_EXTENSION
                    reasoning = f"🚀 [SCALPING EXTENSION] +${pnl:.2f} holding while momentum accelerating ({mom.momentum_score:.0f}/100)"
                else:
                    action = LifecycleAction.PROTECT
                    reasoning = f"🛡️ [SCALPING PROTECT] +${pnl:.2f} secured at BE, watching for scalp target"
                return ContinuationEvaluation(
                    continuation_probability=continuation_prob,
                    continuation_score=continuation_score,
                    lifecycle_action=action,
                    momentum_metrics=mom,
                    volume_metrics=vol,
                    is_structure_intact=is_struct_intact,
                    is_exhaustion_detected=vol.is_exhaustion_detected,
                    reasoning=reasoning,
                )

        # ======================================================================
        # ADAPTIVE PROFIT MANAGER DECISION TREE (project.md Architecture - NORMAL MODE)
        # Evaluates: Profit -> Momentum -> Volume -> Continuation -> Structure -> Exhaustion
        # ======================================================================

        # 1. STRUCTURE EXIT / EMERGENCY EXIT: Clear structural invalidation or hard reversal
        if not is_struct_intact and (not mom.is_favorable_direction or mom.state in (MomentumState.REVERSED, MomentumState.FAILED)):
            action = LifecycleAction.STRUCTURE_EXIT
            reasoning = f"Structure broken with momentum reversal ({mom.state.value}) -> STRUCTURE_EXIT to protect capital."

        elif not mom.is_favorable_direction and continuation_prob < 0.35:
            action = LifecycleAction.EXIT
            reasoning = f"Severe adverse momentum reversal (Cont: {continuation_score:.0f}/100) -> EMERGENCY_EXIT."

        # 2. EXHAUSTION EXIT: Real volume exhaustion + momentum stall + decaying continuation
        # (Only exit on profit when the move is genuinely out of gas, NOT when continuation is 66%!)
        elif pnl >= 0.50 and vol.is_exhaustion_detected and mom.state in (MomentumState.REVERSED, MomentumState.FAILED, MomentumState.PEAK) and continuation_prob < 0.48:
            action = LifecycleAction.EXHAUSTION_EXIT
            reasoning = (
                f"⚡ [ADAPTIVE PROFIT MANAGER] Exhaustion Exit: PnL ${pnl:+.2f}. "
                f"Exhaustion detected & continuation dropped to {continuation_prob*100:.0f}% -> Bank profit before reversal!"
            )

        # 3. PROFIT EXTENSION: In profit with HEALTHY CONTINUATION (e.g. 66%) & intact structure
        # (Directly addresses Step_Index 66% where trade was choked prematurely)
        elif pnl >= 0.30 and continuation_prob >= 0.55 and is_struct_intact and not vol.is_exhaustion_detected:
            action = LifecycleAction.PROFIT_EXTENSION
            reasoning = (
                f"🚀 [ADAPTIVE PROFIT MANAGER] Profit Extension: PnL ${pnl:+.2f} with healthy continuation "
                f"({continuation_prob*100:.0f}%, Vol: {vol.participation_score:.0f}/100). Letting winner run with trailing shield!"
            )

        # 4. STRONG INITIAL MOMENTUM (Pre-profit): Accelerating with volume confirmation
        elif (
            mom.momentum_score >= 60.0
            and mom.state == MomentumState.ACCELERATING
            and vol.volume_state in (VolumeState.EXPANDING, VolumeState.CONFIRMING)
            and is_struct_intact
            and continuation_prob >= 0.55
        ):
            action = LifecycleAction.HOLD
            reasoning = (
                f"Active fuel STRONG! Mom: {mom.momentum_score:.0f}/100 ({mom.tier.value}), "
                f"Vol: {vol.participation_score:.0f}/100, Cont: {continuation_score:.0f}/100 -> MOMENTUM_HOLD."
            )

        # 5. PROFIT PROTECTION: In profit, but momentum is decaying or continuation is cooling (< 55%)
        elif pnl >= 0.30:
            action = LifecycleAction.PROTECT
            reasoning = (
                f"🛡️ [ADAPTIVE PROFIT MANAGER] Profit Protection: PnL ${pnl:+.2f}, "
                f"Continuation: {continuation_prob*100:.0f}%, Mom: {mom.momentum_score:.0f}/100 -> Auto-BE / Trailing Stop active."
            )

        # 6. MOMENTUM DECAY / EXHAUSTION WARNING (Flat or negative position)
        elif vol.is_exhaustion_detected or mom.state in (MomentumState.WEAKENING, MomentumState.PEAK) or continuation_prob < 0.45:
            action = LifecycleAction.MOMENTUM_DECAY
            reasoning = (
                f"Momentum decay detected ({mom.state.value}, {mom.momentum_score:.0f}/100). Cont: {continuation_score:.0f}/100."
            )

        # 7. Default Acceptable Continuation
        elif continuation_prob >= 0.50:
            action = LifecycleAction.HOLD
            reasoning = f"Continuation acceptable ({continuation_score:.0f}/100) -> HOLD"
        else:
            action = LifecycleAction.PROTECT
            reasoning = f"Sub-optimal continuation ({continuation_score:.0f}/100) -> PROTECT"

        return ContinuationEvaluation(
            continuation_probability=continuation_prob,
            continuation_score=continuation_score,
            lifecycle_action=action,
            momentum_metrics=mom,
            volume_metrics=vol,
            is_structure_intact=is_struct_intact,
            is_exhaustion_detected=vol.is_exhaustion_detected,
            reasoning=reasoning,
        )

    @classmethod
    def _check_market_structure(cls, df: pd.DataFrame, is_bullish: bool) -> bool:
        """
        Quick check if local swing structure supports the direction.
        For BUY: latest 3 swing lows are ascending (or latest close > swing midpoint).
        For SELL: latest 3 swing highs are descending (or latest close < swing midpoint).
        """
        if df.empty or len(df) < 6:
            return True

        high = df["high"].values
        low = df["low"].values
        close = df["close"].values
        recent_close = close[-1]

        # Check midpoint of recent 10 bars
        recent_mid = (np.max(high[-10:]) + np.min(low[-10:])) / 2.0

        if is_bullish:
            # Bullish structure is intact if price is above recent midpoint
            # and latest low didn't break recent key low by significant margin
            min_recent_low = np.min(low[-5:])
            prev_low = np.min(low[-10:-5]) if len(low) >= 10 else min_recent_low
            return recent_close >= recent_mid * 0.999 or min_recent_low >= prev_low
        else:
            max_recent_high = np.max(high[-5:])
            prev_high = np.max(high[-10:-5]) if len(high) >= 10 else max_recent_high
            return recent_close <= recent_mid * 1.001 or max_recent_high <= prev_high
