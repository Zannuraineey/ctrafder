"""
Master Trading Engine Orchestrator.
Coordinates Market Scanner, AI Layer, Risk Gatekeeper, Execution, and Monitoring.
Includes Account-Tier Pre-filtering and Post-Mortem Anti-Greed Mistake Prevention.
"""

import asyncio
from typing import Optional, List
from datetime import datetime
from loguru import logger

from app.config.settings import Settings, get_settings
from app.broker.base import BrokerAdapter
from app.broker.paper_broker import PaperBroker
from app.broker.ctrader.adapter import CTraderBrokerAdapter
from app.broker.models import (
    Tick,
    Candle,
    AccountInfo,
    ExitReason,
    Position,
)
from app.market.symbols import SymbolRegistry
from app.market.scanner import MultiMarketScanner, MarketOpportunity
from app.strategies.router import StrategyRouter
from app.ai.inference import AIInferenceEngine
from app.risk.manager import RiskEngine
from app.risk.account_tier import AccountTierEngine
from app.learning.mistake_engine import MistakeEngine, MistakeType
from app.execution.order_manager import OrderManager
from app.execution.position_manager import PositionManager
from app.execution.reconciliation import PositionReconciliation
from app.database.repository import DatabaseRepository
from app.agents.floor import TradingFloor
from app.fundamental.calendar import EconomicCalendar


class TradingEngine:
    """
    Central engine orchestrating the complete AI trading lifecycle.
    """

    def __init__(
        self,
        broker: Optional[BrokerAdapter] = None,
        settings: Optional[Settings] = None,
    ):
        self.settings = settings or get_settings()

        # Initialize Broker Adapter
        if broker is not None:
            self.broker = broker
        elif self.settings.trading_mode == "paper":
            self.broker = PaperBroker(self.settings)
        else:
            self.broker = CTraderBrokerAdapter(self.settings)

        # Core subsystems
        self.registry = SymbolRegistry()
        self.strategy_router = StrategyRouter()
        self.ai_engine = AIInferenceEngine()
        self.floor = TradingFloor(strategy_router=self.strategy_router)
        self.calendar = EconomicCalendar()
        self.scanner = MultiMarketScanner(
            symbol_registry=self.registry,
            strategy_router=self.strategy_router,
            ai_engine=self.ai_engine,
        )
        self.risk_engine = RiskEngine(self.settings)
        self.mistake_engine = MistakeEngine()
        self.order_manager = OrderManager(self.broker)
        self.position_manager = PositionManager(self.broker, self.settings)
        self.reconciliation = PositionReconciliation(self.broker)

        self.is_running = False
        self._loop_task: Optional[asyncio.Task] = None
        self.account_info: Optional[AccountInfo] = None
        self.latest_opportunities: List[MarketOpportunity] = []

    async def start(self) -> None:
        """Start the trading engine lifecycle."""
        logger.info(f"Starting {self.settings.app_name} in [{self.settings.trading_mode.upper()}] mode...")
        connected = await self.broker.connect()
        if not connected:
            logger.error("Failed to connect broker adapter. Engine halting.")
            return

        # Get initial account snapshot
        self.account_info = await self.broker.get_account_info()
        logger.info(f"Initial Account Balance: ${self.account_info.balance:.2f}")

        # Discover instruments and apply Account-Tier Sizing Filter
        raw_symbols = await self.broker.get_symbols()
        scannable_symbols = AccountTierEngine.filter_scannable_symbols(
            raw_symbols, balance=self.account_info.balance
        )
        logger.info(
            f"Account Tier Filter: {len(scannable_symbols)} of {len(raw_symbols)} symbols approved "
            f"for ${self.account_info.balance:.2f} account."
        )

        for s in scannable_symbols:
            self.scanner.register_symbol(s)

        # Subscribe to spot prices
        sym_names = [s.symbol for s in scannable_symbols]
        await self.broker.subscribe_spots(sym_names, self.on_tick_received)

        self.is_running = True
        self._loop_task = asyncio.create_task(self._main_trading_loop())

    async def stop(self) -> None:
        """Gracefully stop the trading engine."""
        logger.info("Stopping trading engine...")
        self.is_running = False
        if self._loop_task:
            self._loop_task.cancel()
        await self.broker.disconnect()
        logger.info("Trading engine stopped.")

    async def emergency_stop(self) -> None:
        """
        Emergency Kill Switch (Section 80 of project.md).
        Immediately closes all open positions and suspends trading.
        """
        logger.critical("EMERGENCY KILL SWITCH TRIGGERED! Closing all open positions...")
        self.is_running = False
        positions = await self.broker.get_open_positions()
        for p in positions:
            await self.broker.close_position(p.id, ExitReason.EMERGENCY_STOP)
        logger.critical("All positions closed. Trading suspended.")

    def on_tick_received(self, tick: Tick) -> None:
        """Feed real-time tick into scanner."""
        self.scanner.ingest_tick(tick)

    async def _main_trading_loop(self) -> None:
        """Periodic scan, evaluation, risk check, execution, and monitoring loop."""
        step = 0
        try:
            while self.is_running:
                step += 1
                try:
                    # 1. Update account state
                    self.account_info = await self.broker.get_account_info()

                    # 2. Monitor active positions (timeouts & stagnation)
                    await self.position_manager.monitor_positions()

                    # 3. Check Anti-Tilt Circuit Breaker
                    is_tilted, tilt_reason = self.mistake_engine.check_floor_tilt_cooldown()
                    if is_tilted:
                        logger.warning(tilt_reason)
                        await asyncio.sleep(self.settings.scan_interval_seconds)
                        continue

                    # 4. Scan all markets & rank candidate setups
                    ranked_opps = self.scanner.scan_all_markets()
                    self.latest_opportunities = ranked_opps

                    # 5. Evaluate top opportunities against Risk Engine & Mistake Engine
                    open_positions = await self.broker.get_open_positions()

                    for opp in ranked_opps:
                        spec = self.registry.get_symbol(opp.symbol)
                        if not spec:
                            continue

                        # Get current tick for spread validation
                        current_tick = getattr(self.broker, "latest_ticks", {}).get(
                            opp.symbol,
                            Tick(symbol=opp.symbol, bid=opp.signal.entry_price, ask=opp.signal.entry_price),
                        )

                        # RUN DETERMINISTIC RISK GATEKEEPER
                        risk_decision = self.risk_engine.evaluate_trade(
                            signal=opp.signal,
                            ai_decision=opp.ai_decision,
                            account=self.account_info,
                            spec=spec,
                            current_tick=current_tick,
                            open_positions=open_positions,
                        )

                        if not risk_decision.approved:
                            continue

                        # RUN POST-MORTEM MISTAKE & ANTI-GREED CHECK
                        mistake_eval = self.mistake_engine.evaluate_pre_trade_mistake(
                            symbol=opp.symbol,
                            balance=self.account_info.balance,
                            risk_percent=risk_decision.risk_percent,
                            regime=opp.regime,
                            whipsaw_prob=opp.whipsaw_probability,
                        )

                        if mistake_eval.has_mistake:
                            logger.warning(f"[MISTAKE ENGINE VETO] {opp.symbol}: {mistake_eval.details}")
                            continue

                        # Execute approved trade
                        order = await self.order_manager.execute_approved_trade(
                            decision=risk_decision,
                            strategy_name=opp.signal.strategy,
                        )
                        # Re-fetch positions to maintain strict concurrency limits
                        open_positions = await self.broker.get_open_positions()

                    # 6. Periodic Snapshot, Reconciliation & Floor Capital Reallocation
                    if step % 30 == 0:
                        DatabaseRepository.save_account_snapshot(
                            self.account_info, self.settings.trading_mode
                        )
                        await self.reconciliation.reconcile()
                        self.floor.reallocate_capital()

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in trading loop cycle: {e}")

                await asyncio.sleep(self.settings.scan_interval_seconds)
        except asyncio.CancelledError:
            pass
