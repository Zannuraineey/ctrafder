"""
Unit tests for the 100-Trader Multi-Agent Floor and Consensus Engine.
"""

import pytest
from app.agents.floor import TradingFloor
from app.agents.agent import TradingAgent
from app.agents.capital_allocator import CapitalAllocator
from app.agents.consensus import ConsensusEngine, AgentVote
from app.broker.models import TradeSignal, TradeSide
from app.fundamental.surprise_engine import FundamentalBias


def test_trading_floor_initialization():
    floor = TradingFloor()
    assert len(floor.agents) == 100

    summary = floor.get_pod_summary()
    assert len(summary) == 4
    for pod_stats in summary.values():
        assert pod_stats["agent_count"] == 25



def test_capital_allocator_probation_and_bonus():
    top_agent = TradingAgent(agent_id=1, name="TopTr", pod_name="Macro")
    for _ in range(2):
        top_agent.record_trade_outcome(-50.0)
    for _ in range(8):
        top_agent.record_trade_outcome(100.0)
    # Win rate = 80%, consecutive losses = 0

    losing_agent = TradingAgent(agent_id=2, name="LossTr", pod_name="Macro")
    for _ in range(4):
        losing_agent.record_trade_outcome(-50.0)
    # 4 consecutive losses

    CapitalAllocator.reallocate_capital([top_agent, losing_agent])

    assert top_agent.capital_weight > 1.20
    assert top_agent.is_probationary is False

    assert losing_agent.capital_weight < 0.50
    assert losing_agent.is_probationary is True


def test_consensus_voting_with_macro_alignment():
    sig_buy = TradeSignal(
        symbol="XAUUSD",
        side=TradeSide.BUY,
        strategy="TEST",
        timeframe="1m",
        entry_price=2350.0,
        stop_loss=2345.0,
        take_profit=2360.0,
    )
    sig_sell = TradeSignal(
        symbol="XAUUSD",
        side=TradeSide.SELL,
        strategy="TEST",
        timeframe="1m",
        entry_price=2350.0,
        stop_loss=2355.0,
        take_profit=2340.0,
    )

    a1 = TradingAgent(1, "A1", "Pod")
    a2 = TradingAgent(2, "A2", "Pod")
    a3 = TradingAgent(3, "A3", "Pod")

    votes = [
        AgentVote(a1, sig_buy),
        AgentVote(a2, sig_buy),
        AgentVote(a3, sig_sell),
    ]

    # Macro bias also bullish
    bias = FundamentalBias("XAUUSD", bias_score=0.80, catalyst="Soft CPI", surprise_z=-2.2)

    consensus = ConsensusEngine.evaluate_consensus("XAUUSD", votes, fundamental_bias=bias)
    assert consensus.side == TradeSide.BUY
    assert consensus.conviction_score > 0.70
    assert consensus.macro_aligned is True
