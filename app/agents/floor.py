"""
Trading Floor Manager: Coordinates the 100-Trader Multi-Agent Pod Architecture.
Institutional Multi-Manager model (Millennium / Citadel style) covering the full Deriv cTrader universe:
- Pod 1: Synthetic Volatilities & Jumps (25 Agents)
- Pod 2: Crash, Boom, Step & Range Break (25 Agents)
- Pod 3: Forex Majors, Minors & Crosses (25 Agents)
- Pod 4: Metals, Energy & Commodities (25 Agents)
Includes account-tier pre-filtering and anti-tilt circuit breakers.
"""

from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
import pandas as pd
from loguru import logger

from app.broker.models import (
    SymbolSpecification,
    MarketRegime,
    TradeSignal,
    TradeSide,
)
from app.agents.agent import TradingAgent
from app.agents.capital_allocator import CapitalAllocator
from app.agents.consensus import ConsensusEngine, AgentVote, ConsensusResult
from app.fundamental.surprise_engine import FundamentalBias
from app.strategies.router import StrategyRouter
from app.market.deriv_universe import AccountTier, DERIV_UNIVERSE_CATALOG, DerivUniverseRegistry


class TradingFloor:
    """
    Manages 100 specialized algorithmic traders across 4 institutional pods,
    covering continuous volatilities, 1s series, crash/boom, step, range break, metals, and FX.
    """

    def __init__(self, strategy_router: Optional[StrategyRouter] = None):
        self.strategy_router = strategy_router or StrategyRouter()
        self.agents: List[TradingAgent] = []
        self._initialize_100_agents()

    def _initialize_100_agents(self) -> None:
        """Construct the floor of 100 specialized algorithmic traders across the full Deriv universe."""
        # 1. Pod 1: Synthetic Volatilities & Jumps (Agents 1-25)
        vol_symbols = [
            "Vol_10", "Vol_25", "Vol_50", "Vol_75", "Vol_100",
            "Vol_10_1s", "Vol_15_1s", "Vol_25_1s", "Vol_30_1s", "Vol_50_1s",
            "Vol_75_1s", "Vol_90_1s", "Vol_100_1s", "Vol_150_1s", "Vol_250_1s",
            "Jump_10", "Jump_25", "Jump_50", "Jump_75", "Jump_100",
            "Dex_600", "Dex_900", "Dex_1500", "Vol_10_1s", "Vol_25_1s",
        ]
        for i in range(1, 26):
            sym = vol_symbols[i - 1]
            meta = DerivUniverseRegistry.get_metadata(sym)
            tier = meta.tier if meta else AccountTier.MEDIUM
            agent = TradingAgent(
                agent_id=i,
                name=f"Synth_Vol_Tr_{i:02d}",
                pod_name="Synthetic Volatility & Jumps Pod",
                specialized_symbols=[sym],
                preferred_regimes=[MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN, MarketRegime.HIGH_VOLATILITY],
                base_strategy_name="DERIV_VOLATILITY",
                account_tier_min=tier,
            )
            self.agents.append(agent)

        # 2. Pod 2: Crash, Boom, Step & Range Break (Agents 26-50)
        spike_symbols = [
            "Crash_300", "Crash_500", "Crash_600", "Crash_900", "Crash_1000",
            "Boom_300", "Boom_500", "Boom_600", "Boom_900", "Boom_1000",
            "Step_Index", "Step_200", "Step_500", "Range_Break_100", "Range_Break_200",
            "Crash_300", "Crash_500", "Boom_300", "Boom_500", "Step_Index",
            "Range_Break_100", "Crash_1000", "Boom_1000", "Step_200", "Range_Break_200",
        ]
        for i in range(26, 51):
            sym = spike_symbols[i - 26]
            meta = DerivUniverseRegistry.get_metadata(sym)
            tier = meta.tier if meta else AccountTier.SMALL
            agent = TradingAgent(
                agent_id=i,
                name=f"Spike_Step_Tr_{i:02d}",
                pod_name="Crash, Boom & Step Pod",
                specialized_symbols=[sym],
                preferred_regimes=[MarketRegime.BREAKOUT, MarketRegime.CHOPPY, MarketRegime.RANGING],
                base_strategy_name="VOLATILITY_BREAKOUT",
                account_tier_min=tier,
            )
            self.agents.append(agent)

        # 3. Pod 3: Forex Majors, Minors & Crosses (Agents 51-75)
        fx_symbols = [
            "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD",
            "USDCAD", "NZDUSD", "EURGBP", "EURJPY", "GBPJPY", "AUDJPY",
            "EURUSD", "GBPUSD", "USDJPY", "EURGBP", "AUDUSD",
            "USDCAD", "USDCHF", "NZDUSD", "GBPJPY", "EURJPY",
            "EURUSD", "GBPUSD", "USDJPY", "AUDJPY",
        ]
        for i in range(51, 76):
            sym = fx_symbols[i - 51]
            meta = DerivUniverseRegistry.get_metadata(sym)
            tier = meta.tier if meta else AccountTier.MICRO
            agent = TradingAgent(
                agent_id=i,
                name=f"Forex_Macro_Tr_{i:02d}",
                pod_name="Forex Majors & Crosses Pod",
                specialized_symbols=[sym],
                preferred_regimes=[MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN, MarketRegime.BREAKOUT],
                base_strategy_name="TREND_PULLBACK",
                account_tier_min=tier,
            )
            self.agents.append(agent)

        # 4. Pod 4: Metals, Energy & Commodities (Agents 76-100)
        metal_symbols = [
            "XAUUSD", "XAGUSD", "XPTUSD", "XPDUSD", "US_OIL", "UK_OIL",
            "BTCUSD", "ETHUSD", "XAUUSD", "XAUUSD", "XAGUSD", "US_OIL",
            "XAUUSD", "BTCUSD", "ETHUSD", "XAGUSD", "UK_OIL", "XAUUSD",
            "XPTUSD", "XAUUSD", "US_OIL", "XAGUSD", "BTCUSD", "ETHUSD", "XAUUSD",
        ]
        for i in range(76, 101):
            sym = metal_symbols[i - 76]
            meta = DerivUniverseRegistry.get_metadata(sym)
            tier = meta.tier if meta else AccountTier.MEDIUM
            agent = TradingAgent(
                agent_id=i,
                name=f"Commodity_Gold_Tr_{i:02d}",
                pod_name="Metals, Energy & Commodities Pod",
                specialized_symbols=[sym],
                preferred_regimes=[MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN, MarketRegime.HIGH_VOLATILITY],
                base_strategy_name="MOMENTUM",
                account_tier_min=tier,
            )
            self.agents.append(agent)

        logger.info(f"Initialized Trading Floor with {len(self.agents)} autonomous agents covering 50+ Deriv instruments across 4 pods.")

    def run_floor_evaluation(
        self,
        symbol: str,
        features_df: pd.DataFrame,
        regime: MarketRegime,
        spec: SymbolSpecification,
        fundamental_bias: Optional[FundamentalBias] = None,
        higher_tf_features_df: Optional[pd.DataFrame] = None,
        current_balance: Optional[float] = None,
    ) -> ConsensusResult:
        """
        Poll all agents eligible for this symbol, regime, and account tier, collect votes,
        and calculate institutional consensus.
        """
        eligible_agents = [
            a
            for a in self.agents
            if a.is_eligible_for_symbol_and_regime(symbol, regime, current_balance)
        ]

        # Generate candidate strategy signals
        candidates = self.strategy_router.route_and_evaluate(
            symbol=symbol,
            features_df=features_df,
            regime=regime,
            spec=spec,
            higher_tf_features_df=higher_tf_features_df,
        )

        if not candidates or not eligible_agents:
            return ConsensusResult(
                symbol=symbol,
                side=None,
                conviction_score=0.0,
                winning_signal=None,
                participating_agents=0,
                buy_weight=0.0,
                sell_weight=0.0,
            )

        # Cast votes from eligible agents
        votes: List[AgentVote] = []
        for agent in eligible_agents:
            best_sig = candidates[0]
            votes.append(AgentVote(agent=agent, signal=best_sig))

        consensus = ConsensusEngine.evaluate_consensus(
            symbol=symbol,
            votes=votes,
            fundamental_bias=fundamental_bias,
        )
        return consensus

    def reallocate_capital(self) -> None:
        """Trigger capital reallocation across all 100 traders."""
        CapitalAllocator.reallocate_capital(self.agents)

    def apply_agent_penalty(self, agent_id: int, reason: str, minutes: int = 30) -> None:
        """Bench a specific agent who committed a mistake."""
        for a in self.agents:
            if a.agent_id == agent_id:
                a.apply_penalty(reason, minutes)
                logger.warning(f"[PENALTY BOX] Agent #{a.agent_id} ({a.name}) benched for {minutes}m: {reason}")
                break

    def get_pod_summary(self) -> Dict[str, Dict[str, Any]]:
        """Return performance statistics grouped by Pod."""
        summary: Dict[str, Dict[str, Any]] = {}
        for a in self.agents:
            p = summary.setdefault(
                a.pod_name,
                {"agent_count": 0, "active_count": 0, "total_trades": 0, "wins": 0, "pnl": 0.0, "avg_weight": 0.0},
            )
            p["agent_count"] += 1
            if not a.is_in_penalty_box():
                p["active_count"] += 1
            p["total_trades"] += a.trades_count
            p["wins"] += a.wins_count
            p["pnl"] += a.total_pnl
            p["avg_weight"] += a.capital_weight

        for p in summary.values():
            if p["agent_count"] > 0:
                p["avg_weight"] = round(p["avg_weight"] / p["agent_count"], 2)
                p["win_rate"] = (
                    round(p["wins"] / p["total_trades"], 3) if p["total_trades"] > 0 else 0.50
                )
        return summary
