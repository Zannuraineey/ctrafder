"""
Active Position Monitoring & Scalping Timeout / Stagnation Engine.
Section 34, 35, and 37 of project.md.
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime
from loguru import logger

from app.config.settings import Settings, get_settings
from app.broker.base import BrokerAdapter
from app.broker.models import Position, ExitReason, TradeSide, Tick, PositionStatus
from app.execution.continuation_engine import ContinuationEngine, LifecycleAction
import pandas as pd


class PositionManager:
    """
    Monitors open positions using Continuation Engine and Trade Lifecycle Manager (HOLD, PROTECT, EXIT).
    Avoids prematurely closing strong trending trades on arbitrary fixed seconds.
    """

    def __init__(self, broker: BrokerAdapter, settings: Optional[Settings] = None):
        self.broker = broker
        self.settings = settings or get_settings()
        self._price_progress: Dict[str, List[float]] = {}

    async def monitor_positions(self, candle_cache: Optional[Dict[str, List[dict]]] = None) -> List[Tuple[str, ExitReason]]:
        """
        Evaluate all open positions using Continuation Engine.
        Returns list of (position_id, exit_reason) to close.
        """
        open_positions = await self.broker.get_open_positions()
        exits_to_execute: List[Tuple[str, ExitReason]] = []

        for pos in open_positions:
            if pos.status != PositionStatus.OPEN:
                continue

            duration = pos.duration_seconds
            c_list = candle_cache.get(pos.symbol, []) if candle_cache else []

            # If we have candle history, evaluate Continuation Engine
            if len(c_list) >= 5:
                df = pd.DataFrame(c_list)
                cont_eval = ContinuationEngine.evaluate_active_position(pos, df)
                pos.momentum_score = cont_eval.momentum_metrics.momentum_score
                pos.volume_rvol = cont_eval.volume_metrics.rvol
                pos.continuation_prob = cont_eval.continuation_probability
                pos.lifecycle_action = cont_eval.lifecycle_action.value

                # 1. HOLD DECISION: Let winning trades expand!
                if cont_eval.lifecycle_action == LifecycleAction.HOLD:
                    logger.info(
                        f"[LIFECYCLE HOLD] {pos.symbol} {pos.side.value} (PnL: ${pos.unrealized_pnl:+.2f}, "
                        f"Mom: {pos.momentum_score:.0f}, Vol RVOL: {pos.volume_rvol}, Cont: {pos.continuation_prob*100:.0f}%) -> HOLD"
                    )
                    # Never force timeout exit while trade has strong continuation fuel!
                    continue

                # 2. SCALP PROFIT TAKE: Profit >= $0.50 with fading momentum -> SNATCH IT
                elif cont_eval.lifecycle_action == LifecycleAction.SCALP_TAKE:
                    logger.info(
                        f"🎯 [PROFIT HUNT] Snatching ${pos.unrealized_pnl:+.2f} profit on {pos.symbol} "
                        f"(Mom: {pos.momentum_score:.0f}, Cont: {pos.continuation_prob*100:.0f}%) -> AUTO-CLOSE"
                    )
                    exits_to_execute.append((pos.id, ExitReason.TAKE_PROFIT))
                    continue

                # 3. PROTECT DECISION: Fading momentum -> Lock in BE/Trailing
                elif cont_eval.lifecycle_action == LifecycleAction.PROTECT:
                    if pos.unrealized_pnl > 0.50 and not getattr(pos, "is_be_active", False):
                        await self.broker.move_to_breakeven(pos.id)
                        logger.info(f"[LIFECYCLE PROTECT] Moved {pos.symbol} to BE due to weakening continuation")

                # 4. EXIT DECISION: Momentum reversed or continuation failed
                elif cont_eval.lifecycle_action == LifecycleAction.EXIT:
                    logger.info(
                        f"[LIFECYCLE EXIT] Momentum failed / reversed on {pos.symbol}. Closing position."
                    )
                    exits_to_execute.append((pos.id, ExitReason.SIGNAL))
                    continue

            # Fallback for stagnant / lingering non-profitable trades
            # 1. Stagnation check
            history = self._price_progress.setdefault(pos.id, [])
            history.append(pos.current_price)
            if len(history) >= self.settings.stagnation_candle_count:
                recent_window = history[-self.settings.stagnation_candle_count :]
                entry_dist = abs(pos.current_price - pos.entry_price)
                if duration > 45 and entry_dist < (pos.entry_price * 0.0002) and pos.unrealized_pnl <= 0:
                    logger.info(f"[STAGNATION EXIT] Position {pos.id} ({pos.symbol}) stagnant for {duration}s.")
                    exits_to_execute.append((pos.id, ExitReason.STAGNATION))
                    continue

            # 2. Losing trade lingering beyond soft timeout without recovery momentum
            if duration >= self.settings.soft_timeout_seconds and pos.unrealized_pnl < 0.0:
                logger.info(f"[TIMEOUT EXIT] Losing position {pos.id} past {self.settings.soft_timeout_seconds}s.")
                exits_to_execute.append((pos.id, ExitReason.TIMEOUT))

        # Execute identified exits
        for pos_id, reason in exits_to_execute:
            await self.broker.close_position(pos_id, reason)
            if pos_id in self._price_progress:
                del self._price_progress[pos_id]

        return exits_to_execute
