"""
Post-Mortem Mistake Learning & Anti-Greed Engine.
Detects revenge trading, greed oversizing, choppy overtrading, and spike blowouts.
Places undisciplined agents into a cooling-off Penalty Box and provides an AI Mistake Memory
that blocks trades mirroring historical blowout states.
"""

from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import numpy as np
from loguru import logger
from pydantic import BaseModel

from app.broker.models import TradeRecord, TradeSignal, MarketRegime, SymbolSpecification
from app.database.repository import DatabaseRepository


class MistakeType:
    REVENGE_TRADING = "REVENGE_TRADING"
    GREED_OVERSIZING = "GREED_OVERSIZING"
    CHOPPY_OVERTRADING = "CHOPPY_OVERTRADING"
    SPIKE_MARGIN_BLOWOUT = "SPIKE_MARGIN_BLOWOUT"
    ACCOUNT_TIER_VIOLATION = "ACCOUNT_TIER_VIOLATION"
    PREMATURE_PANIC_EXIT = "PREMATURE_PANIC_EXIT"


class MistakeEvaluation(BaseModel):
    has_mistake: bool
    mistake_type: Optional[str] = None
    details: Optional[str] = None
    action_taken: str = "NONE"
    penalty_cooldown_minutes: int = 0


class MistakeMemoryItem(BaseModel):
    mistake_type: str
    symbol: str
    feature_vector: List[float]
    loss_amount: float
    timestamp: datetime


class MistakeEngine:
    """
    Analyzes trade executions and patterns to prevent emotional, undisciplined trading.
    """

    def __init__(self):
        self._last_loss_timestamps: Dict[str, datetime] = {}  # symbol -> last loss time
        self._consecutive_losses: int = 0
        self._floor_cooldown_until: Optional[datetime] = None
        self._mistake_memory: List[MistakeMemoryItem] = []
        self._init_memory_from_db()

    def _init_memory_from_db(self) -> None:
        """Load recent historical mistake vectors into working memory."""
        try:
            recent = DatabaseRepository.get_recent_mistakes(limit=30)
            for m in recent:
                feat = m.get("feature_snapshot", {})
                vec = self._extract_vector(feat)
                if vec is not None:
                    self._mistake_memory.append(
                        MistakeMemoryItem(
                            mistake_type=m["mistake_type"],
                            symbol=m["symbol"],
                            feature_vector=vec,
                            loss_amount=m["loss_amount"],
                            timestamp=m["timestamp"],
                        )
                    )
        except Exception as ex:
            logger.debug(f"Mistake memory initialization note: {ex}")

    @staticmethod
    def _extract_vector(feat_dict: Dict[str, Any]) -> Optional[List[float]]:
        keys = ["whipsaw_probability", "atr_ratio", "spread_ratio", "adx_14", "rsi_14", "clv"]
        if all(k in feat_dict for k in keys):
            return [float(feat_dict[k]) for k in keys]
        return None

    def check_floor_tilt_cooldown(self) -> Tuple[bool, Optional[str]]:
        """Check if entire floor is suspended under an anti-tilt circuit breaker."""
        now = datetime.utcnow()
        if self._floor_cooldown_until and now < self._floor_cooldown_until:
            rem_sec = int((self._floor_cooldown_until - now).total_seconds())
            return (
                True,
                f"[FLOOR ANTI-TILT COOLDOWN] Floor paused for another {rem_sec}s after 2 consecutive portfolio losses.",
            )
        return False, None

    def evaluate_pre_trade_mistake(
        self,
        symbol: str,
        balance: float,
        risk_percent: float,
        regime: MarketRegime,
        whipsaw_prob: float,
        features_dict: Optional[Dict[str, Any]] = None,
    ) -> MistakeEvaluation:
        """
        Pre-flight check before trade submission to intercept revenge trading and greed oversizing.
        """
        now = datetime.utcnow()

        # 1. Revenge Trading Check (< 180s after previous loss on this symbol)
        last_loss = self._last_loss_timestamps.get(symbol)
        if last_loss is not None:
            sec_since_loss = (now - last_loss).total_seconds()
            if sec_since_loss < 180.0:
                details = (
                    f"Candidate trade on {symbol} submitted {sec_since_loss:.0f}s after previous loss. "
                    f"Revenge trading prohibited within 180s cool-off window."
                )
                return MistakeEvaluation(
                    has_mistake=True,
                    mistake_type=MistakeType.REVENGE_TRADING,
                    details=details,
                    action_taken="PRE_TRADE_VETO",
                    penalty_cooldown_minutes=15,
                )

        # 2. Greed Oversizing Check (> 2.5% risk on a single trade)
        if risk_percent > 0.025:
            details = (
                f"Attempted risk of {risk_percent*100:.1f}% exceeds max institutional 2.0% allocation. "
                f"Greed sizing is the #1 cause of blown accounts."
            )
            return MistakeEvaluation(
                has_mistake=True,
                mistake_type=MistakeType.GREED_OVERSIZING,
                details=details,
                action_taken="PRE_TRADE_VETO",
                penalty_cooldown_minutes=30,
            )

        # 3. Choppy Overtrading Check (Whipsaw > 65% or Choppy regime)
        if regime in (MarketRegime.CHOPPY, MarketRegime.RANGING) and whipsaw_prob > 0.65:
            details = (
                f"Attempted entry during {regime.value} with elevated whipsaw index ({whipsaw_prob*100:.1f}%). "
                f"High probability of false breakout trap."
            )
            return MistakeEvaluation(
                has_mistake=True,
                mistake_type=MistakeType.CHOPPY_OVERTRADING,
                details=details,
                action_taken="PRE_TRADE_VETO",
                penalty_cooldown_minutes=20,
            )

        # 4. AI Mistake Memory Pattern Similarity Check
        if features_dict and self._mistake_memory:
            cand_vec = self._extract_vector(features_dict)
            if cand_vec is not None:
                sim, matched = self._find_max_similarity(cand_vec)
                if sim >= 0.85:
                    details = (
                        f"Current market structure has {sim*100:.1f}% similarity to past blowout pattern "
                        f"({matched.mistake_type} on {matched.symbol}, loss: ${matched.loss_amount:.2f})."
                    )
                    return MistakeEvaluation(
                        has_mistake=True,
                        mistake_type="AI_MISTAKE_MEMORY_MATCH",
                        details=details,
                        action_taken="PRE_TRADE_VETO",
                        penalty_cooldown_minutes=10,
                    )

        return MistakeEvaluation(has_mistake=False)

    def evaluate_post_trade_outcome(
        self, trade: TradeRecord, agent_id: Optional[int] = None, current_balance: float = 10000.0
    ) -> Optional[MistakeEvaluation]:
        """
        Examines closed trade to update loss tracking, anti-tilt circuit breakers, and mistake memory.
        """
        now = datetime.utcnow()
        if trade.profit_loss < 0:
            self._last_loss_timestamps[trade.symbol] = now
            self._consecutive_losses += 1

            # Check if loss triggered anti-tilt floor cooldown (>= 2 consecutive losses)
            if self._consecutive_losses >= 2:
                self._floor_cooldown_until = now + timedelta(minutes=15)
                logger.warning(
                    f"[ANTI-TILT ACTIVATED] 2 consecutive losses detected. Floor frozen for 15 minutes."
                )

            # Check for Spike Blowout on Crash/Boom/Vol synthetics
            loss_ratio = abs(trade.profit_loss) / max(current_balance, 1.0)
            if loss_ratio > 0.04 and ("Crash" in trade.symbol or "Boom" in trade.symbol or "Vol" in trade.symbol):
                details = (
                    f"Catastrophic spike loss on {trade.symbol} (${trade.profit_loss:.2f}, {loss_ratio*100:.1f}% of equity). "
                    f"Stop loss failed or position held against jump process."
                )
                DatabaseRepository.save_trade_mistake(
                    symbol=trade.symbol,
                    mistake_type=MistakeType.SPIKE_MARGIN_BLOWOUT,
                    details=details,
                    trade_id=trade.trade_id,
                    agent_id=agent_id,
                    loss_amount=abs(trade.profit_loss),
                    account_balance=current_balance,
                    risk_percent=trade.risk_percent,
                    action_taken="AGENT_PENALTY_BOX_60M",
                )
                return MistakeEvaluation(
                    has_mistake=True,
                    mistake_type=MistakeType.SPIKE_MARGIN_BLOWOUT,
                    details=details,
                    action_taken="AGENT_PENALTY_BOX_60M",
                    penalty_cooldown_minutes=60,
                )
        else:
            # Winning trade resets consecutive losses
            self._consecutive_losses = 0

        return None

    def _find_max_similarity(self, cand_vec: List[float]) -> Tuple[float, MistakeMemoryItem]:
        """Compute maximum cosine similarity between candidate vector and historical blowout vectors."""
        v1 = np.array(cand_vec)
        norm_v1 = np.linalg.norm(v1)
        if norm_v1 <= 1e-9:
            return 0.0, self._mistake_memory[0]

        best_sim = -1.0
        best_item = self._mistake_memory[0]

        for item in self._mistake_memory:
            v2 = np.array(item.feature_vector)
            norm_v2 = np.linalg.norm(v2)
            if norm_v2 > 1e-9:
                cos_sim = float(np.dot(v1, v2) / (norm_v1 * norm_v2))
                if cos_sim > best_sim:
                    best_sim = cos_sim
                    best_item = item

        return max(0.0, best_sim), best_item
