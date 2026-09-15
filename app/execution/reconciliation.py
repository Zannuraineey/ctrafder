"""
Two-Way State Reconciliation Engine.
Synchronizes local trade/order registry against authoritative broker state (cTrader / Paper).
Detects external manual trades, broker-side SL/TP executions, and volume/fill discrepancies.
"""

from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger

from app.broker.base import BrokerAdapter
from app.broker.models import Position, PositionStatus, ExitReason, AccountInfo


@dataclass
class ReconciliationReport:
    timestamp: datetime
    broker_positions_count: int
    local_positions_count: int
    missing_in_broker: List[str] = field(default_factory=list)      # Closed on broker (SL/TP/liquidation)
    unmapped_in_broker: List[str] = field(default_factory=list)    # External manual trades on broker
    volume_mismatches: List[Dict[str, Any]] = field(default_factory=list)
    sl_tp_mismatches: List[Dict[str, Any]] = field(default_factory=list)
    is_synchronized: bool = True
    actions_taken: List[str] = field(default_factory=list)


class InstitutionalReconciliationWorker:
    """
    Periodic background reconciliation worker.
    The broker is ALWAYS the authoritative source of truth.
    """

    def __init__(self, broker: BrokerAdapter):
        self.broker = broker
        self.last_report: Optional[ReconciliationReport] = None
        self.reconciliation_count = 0

    async def reconcile(
        self,
        local_positions: List[Position],
        auto_heal: bool = True,
    ) -> Tuple[List[Position], ReconciliationReport]:
        """
        Reconcile local state with broker reality.
        Returns:
            reconciled_positions: List[Position] matching broker ground truth
            report: Detailed audit report of discrepancies
        """
        now = datetime.utcnow()
        self.reconciliation_count += 1

        try:
            broker_positions = await self.broker.get_open_positions()
        except Exception as e:
            logger.error(f"Failed to query broker positions for reconciliation: {e}")
            report = ReconciliationReport(
                timestamp=now,
                broker_positions_count=0,
                local_positions_count=len(local_positions),
                is_synchronized=False,
                actions_taken=[f"RECONCILIATION_ERROR: {str(e)}"],
            )
            return local_positions, report

        broker_map: Dict[str, Position] = {p.id: p for p in broker_positions}
        local_map: Dict[str, Position] = {p.id: p for p in local_positions}

        missing_in_broker: List[str] = []
        unmapped_in_broker: List[str] = []
        volume_mismatches: List[Dict[str, Any]] = []
        sl_tp_mismatches: List[Dict[str, Any]] = []
        actions_taken: List[str] = []

        # 1. Detect positions in local state that are missing from broker
        for pos_id, local_pos in local_map.items():
            if pos_id not in broker_map:
                missing_in_broker.append(pos_id)
                if auto_heal:
                    local_pos.status = PositionStatus.CLOSED
                    local_pos.closed_at = now
                    local_pos.exit_reason = ExitReason.RECONCILIATION
                    actions_taken.append(
                        f"HEALED_ORPHAN_LOCAL: Position #{pos_id} marked CLOSED (vanished on broker)."
                    )

        # 2. Detect external positions on broker that local state does not have
        for pos_id, broker_pos in broker_map.items():
            if pos_id not in local_map:
                unmapped_in_broker.append(pos_id)
                if auto_heal:
                    actions_taken.append(
                        f"INGESTED_EXTERNAL_BROKER: Position #{pos_id} ({broker_pos.symbol}) mapped into local tracking."
                    )

        # 3. Detect parameter discrepancies for overlapping positions
        for pos_id, b_pos in broker_map.items():
            if pos_id in local_map:
                l_pos = local_map[pos_id]
                # Check volume mismatch
                if abs(b_pos.volume - l_pos.volume) > 1e-4:
                    volume_mismatches.append({
                        "id": pos_id,
                        "symbol": b_pos.symbol,
                        "local_volume": l_pos.volume,
                        "broker_volume": b_pos.volume,
                    })
                    if auto_heal:
                        l_pos.volume = b_pos.volume
                        actions_taken.append(f"ALIGNED_VOLUME #{pos_id}: Updated volume to {b_pos.volume}")

                # Check SL / TP drift
                if abs(b_pos.stop_loss - l_pos.stop_loss) > 1e-3 or abs(b_pos.take_profit - l_pos.take_profit) > 1e-3:
                    sl_tp_mismatches.append({
                        "id": pos_id,
                        "local_sl": l_pos.stop_loss,
                        "broker_sl": b_pos.stop_loss,
                        "local_tp": l_pos.take_profit,
                        "broker_tp": b_pos.take_profit,
                    })
                    if auto_heal:
                        l_pos.stop_loss = b_pos.stop_loss
                        l_pos.take_profit = b_pos.take_profit
                        actions_taken.append(f"ALIGNED_SL_TP #{pos_id}: Synced SL={b_pos.stop_loss}, TP={b_pos.take_profit}")

        # Assemble final reconciled list (authoritative broker positions)
        if auto_heal:
            # Preserve enriched AI metrics from local instances where matched
            final_positions: List[Position] = []
            for b_pos in broker_positions:
                if b_pos.id in local_map:
                    l = local_map[b_pos.id]
                    b_pos.strategy = getattr(l, "strategy", b_pos.strategy)
                    b_pos.momentum_score = getattr(l, "momentum_score", 50.0)
                    b_pos.volume_rvol = getattr(l, "volume_rvol", 1.0)
                    b_pos.continuation_prob = getattr(l, "continuation_prob", 0.5)
                    b_pos.lifecycle_action = getattr(l, "lifecycle_action", "HOLD")
                    b_pos.is_be_active = getattr(l, "is_be_active", False)
                final_positions.append(b_pos)
        else:
            final_positions = local_positions

        is_clean = len(missing_in_broker) == 0 and len(unmapped_in_broker) == 0 and len(volume_mismatches) == 0

        report = ReconciliationReport(
            timestamp=now,
            broker_positions_count=len(broker_positions),
            local_positions_count=len(local_positions),
            missing_in_broker=missing_in_broker,
            unmapped_in_broker=unmapped_in_broker,
            volume_mismatches=volume_mismatches,
            sl_tp_mismatches=sl_tp_mismatches,
            is_synchronized=is_clean,
            actions_taken=actions_taken,
        )

        self.last_report = report
        if not is_clean:
            logger.warning(
                f"[RECONCILIATION] Discrepancies resolved: {len(missing_in_broker)} orphan local, "
                f"{len(unmapped_in_broker)} external broker, {len(volume_mismatches)} volume diffs."
            )
        return final_positions, report


# Maintain PositionReconciliation class name for backwards compatibility
class PositionReconciliation:
    """Wrapper providing backwards compatibility for PositionReconciliation."""

    def __init__(self, broker: BrokerAdapter):
        self.worker = InstitutionalReconciliationWorker(broker)

    async def reconcile(self) -> List[Position]:
        positions, _ = await self.worker.reconcile(local_positions=[], auto_heal=True)
        return positions
