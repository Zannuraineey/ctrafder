"""
Multi-Agent Consensus & Conviction Engine.
Aggregates votes across specialized agents to compute institutional conviction.
"""

from typing import List, Dict, Optional, Tuple
from app.broker.models import TradeSignal, TradeSide
from app.agents.agent import TradingAgent
from app.fundamental.surprise_engine import FundamentalBias


class AgentVote:
    """Individual trader vote on a trade proposal."""

    def __init__(self, agent: TradingAgent, signal: TradeSignal):
        self.agent = agent
        self.signal = signal
        self.weighted_vote = agent.capital_weight


class ConsensusResult:
    """Consensus voting outcome across the trading floor."""

    def __init__(
        self,
        symbol: str,
        side: Optional[TradeSide],
        conviction_score: float,  # 0.0 to 1.0 (90%+ = High Conviction Institutional Consensus)
        winning_signal: Optional[TradeSignal],
        participating_agents: int,
        buy_weight: float,
        sell_weight: float,
        macro_aligned: bool = False,
    ):
        self.symbol = symbol
        self.side = side
        self.conviction_score = conviction_score
        self.winning_signal = winning_signal
        self.participating_agents = participating_agents
        self.buy_weight = buy_weight
        self.sell_weight = sell_weight
        self.macro_aligned = macro_aligned


class ConsensusEngine:
    """
    Evaluates multi-agent votes and incorporates macroeconomic alignment.
    """

    @classmethod
    def evaluate_consensus(
        cls,
        symbol: str,
        votes: List[AgentVote],
        fundamental_bias: Optional[FundamentalBias] = None,
    ) -> ConsensusResult:
        if not votes:
            return ConsensusResult(
                symbol=symbol,
                side=None,
                conviction_score=0.0,
                winning_signal=None,
                participating_agents=0,
                buy_weight=0.0,
                sell_weight=0.0,
            )

        buy_weight = sum(v.weighted_vote for v in votes if v.signal.side == TradeSide.BUY)
        sell_weight = sum(v.weighted_vote for v in votes if v.signal.side == TradeSide.SELL)
        total_weight = buy_weight + sell_weight

        if total_weight <= 0:
            return ConsensusResult(
                symbol=symbol,
                side=None,
                conviction_score=0.0,
                winning_signal=None,
                participating_agents=len(votes),
                buy_weight=0.0,
                sell_weight=0.0,
            )

        # Determine dominant direction
        if buy_weight > sell_weight:
            dominant_side = TradeSide.BUY
            raw_conviction = buy_weight / total_weight
            winning_signal = next(v.signal for v in votes if v.signal.side == TradeSide.BUY)
        else:
            dominant_side = TradeSide.SELL
            raw_conviction = sell_weight / total_weight
            winning_signal = next(v.signal for v in votes if v.signal.side == TradeSide.SELL)

        # Macro Alignment Boost / Penalty
        macro_aligned = False
        if fundamental_bias is not None and fundamental_bias.recommended_side is not None:
            if fundamental_bias.recommended_side == dominant_side:
                raw_conviction = min(1.0, raw_conviction + 0.15)
                macro_aligned = True
            else:
                raw_conviction = max(0.1, raw_conviction - 0.25)

        return ConsensusResult(
            symbol=symbol,
            side=dominant_side,
            conviction_score=round(raw_conviction, 3),
            winning_signal=winning_signal,
            participating_agents=len(votes),
            buy_weight=round(buy_weight, 2),
            sell_weight=round(sell_weight, 2),
            macro_aligned=macro_aligned,
        )
