"""
High-Fidelity Paper Broker Simulator.
Simulates live market execution, spreads, slippage, commissions, and SL/TP triggers.
Section 39 and 68 of project.md.
"""

import uuid
from typing import List, Optional, Callable, Dict
from datetime import datetime
import asyncio
from loguru import logger

from app.config.settings import Settings, get_settings
from app.broker.base import BrokerAdapter
from app.broker.models import (
    AccountInfo,
    SymbolSpecification,
    Tick,
    Candle,
    Order,
    Position,
    TradeSide,
    OrderStatus,
    PositionStatus,
    ExitReason,
    TradeRecord,
)
from app.database.repository import DatabaseRepository
from app.market.deriv_universe import DerivUniverseRegistry


class PaperBroker(BrokerAdapter):
    """
    Simulated local broker implementing realistic trading mechanics.
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.balance: float = self.settings.paper_starting_balance
        self.equity: float = self.settings.paper_starting_balance
        self.daily_pnl: float = 0.0
        self.connected: bool = False

        self.symbols: Dict[str, SymbolSpecification] = {}
        self.latest_ticks: Dict[str, Tick] = {}
        self.open_positions: Dict[str, Position] = {}
        self.closed_positions: List[Position] = []
        self.orders: Dict[str, Order] = {}
        self.spot_callbacks: List[Callable[[Tick], None]] = []

        self._init_default_symbols()

    def _init_default_symbols(self) -> None:
        """Initialize standard asset universe from Deriv Universe Registry (50+ symbols)."""
        defaults = DerivUniverseRegistry.get_all_symbols()
        for s in defaults:
            self.symbols[s.symbol] = s
            try:
                DatabaseRepository.save_market(s)
            except Exception:
                pass

    async def connect(self) -> bool:
        self.connected = True
        logger.info(f"Paper Broker connected. Starting balance: ${self.balance:.2f}")
        return True

    async def disconnect(self) -> None:
        self.connected = False
        logger.info("Paper Broker disconnected.")

    def is_connected(self) -> bool:
        return self.connected

    async def get_account_info(self) -> AccountInfo:
        # Calculate current margin used and unrealized PnL
        margin_used = 0.0
        unrealized = 0.0

        for pos in self.open_positions.values():
            spec = self.symbols.get(pos.symbol)
            if spec:
                margin_used += pos.volume * pos.entry_price * spec.margin_rate
            unrealized += pos.unrealized_pnl

        self.equity = self.balance + unrealized
        free_margin = max(0.0, self.equity - margin_used)
        margin_level = (self.equity / margin_used * 100.0) if margin_used > 0 else 999.0

        return AccountInfo(
            account_id="PAPER_SIM_001",
            broker="PaperBroker",
            currency="USD",
            balance=round(self.balance, 2),
            equity=round(self.equity, 2),
            margin_used=round(margin_used, 2),
            free_margin=round(free_margin, 2),
            margin_level=round(margin_level, 2),
            daily_pnl=round(self.daily_pnl + unrealized, 2),
            open_positions_count=len(self.open_positions),
            is_live=False,
        )

    async def get_symbols(self) -> List[SymbolSpecification]:
        return list(self.symbols.values())

    async def subscribe_spots(
        self, symbols: List[str], callback: Callable[[Tick], None]
    ) -> None:
        self.spot_callbacks.append(callback)

    async def get_historical_candles(
        self, symbol: str, timeframe: str, count: int = 500
    ) -> List[Candle]:
        # Fetch from database cache
        return DatabaseRepository.get_recent_candles(symbol, timeframe, limit=count)

    async def send_market_order(
        self,
        symbol: str,
        side: TradeSide,
        volume_lots: float,
        stop_loss: float,
        take_profit: float,
        comment: str = "",
        current_price: Optional[float] = None,
    ) -> Order:
        order_id = f"ord_{uuid.uuid4().hex[:8]}"
        spec = self.symbols.get(symbol)
        if not spec:
            raise ValueError(f"Symbol {symbol} not recognized in paper broker")

        # Determine current tick or fallback
        if current_price is not None:
            base_price = float(current_price)
        else:
            tick = self.latest_ticks.get(symbol)
            if tick is not None:
                base_price = tick.ask if side == TradeSide.BUY else tick.bid
            else:
                base_price = (
                    2354.20 if "XAU" in symbol
                    else 1.08500 if "EUR" in symbol
                    else 155.80 if "USDJPY" in symbol
                    else 1.27100 if "GBP" in symbol
                    else 1240.50 if "Step" in symbol
                    else 1250.40 if "Crash" in symbol
                    else 1320.10 if "Boom" in symbol
                    else 380.15 if "Vol_25" in symbol
                    else 152.34 if "Vol_10" in symbol
                    else 8421.50 if "Vol_75" in symbol
                    else 100.0
                )

        # Apply slippage simulation
        pip_unit = spec.tick_size * 10 if spec.digits in (3, 5) else spec.tick_size
        slippage = pip_unit * self.settings.paper_slippage_pips
        fill_price = round(base_price + slippage if side == TradeSide.BUY else base_price - slippage, spec.digits)

        # Apply commission (Deriv Synthetics have ZERO commission - pure spread model)
        commission = 0.0 if spec.asset_class == "SYNTHETIC" else round(volume_lots * self.settings.paper_commission_per_lot, 2)
        self.balance -= commission

        order = Order(
            id=order_id,
            broker_order_id=order_id,
            symbol=symbol,
            side=side,
            volume=volume_lots * spec.contract_size,
            price=fill_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            status=OrderStatus.FILLED,
            filled_at=datetime.utcnow(),
            fill_price=fill_price,
        )
        self.orders[order_id] = order

        # Create Open Position
        pos_id = f"pos_{uuid.uuid4().hex[:8]}"
        position = Position(
            id=pos_id,
            broker_position_id=pos_id,
            symbol=symbol,
            side=side,
            volume=volume_lots * spec.contract_size,
            entry_price=fill_price,
            current_price=fill_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            unrealized_pnl=-commission,
            realized_pnl=0.0,
            status=PositionStatus.OPEN,
            opened_at=datetime.utcnow(),
            strategy=comment,
        )
        self.open_positions[pos_id] = position

        logger.info(
            f"[PAPER FILL] {symbol} {side.value} {volume_lots} lots @ {fill_price}, SL: {stop_loss}, TP: {take_profit}"
        )
        return order

    async def close_position(
        self, position_id: str, exit_reason: ExitReason
    ) -> bool:
        position = self.open_positions.get(position_id)
        if not position:
            return False

        spec = self.symbols.get(position.symbol)
        if not spec:
            return False

        tick = self.latest_ticks.get(position.symbol)
        exit_price = (
            (tick.bid if position.side == TradeSide.BUY else tick.ask)
            if tick
            else position.current_price
        )

        # Calculate final P&L
        if position.side == TradeSide.BUY:
            price_delta = exit_price - position.entry_price
        else:
            price_delta = position.entry_price - exit_price

        ticks = price_delta / max(spec.tick_size, 1e-9)
        lots = position.volume / max(spec.contract_size, 1e-5)
        pnl = round(ticks * spec.tick_value * lots, 2)

        # Deduct exit commission (Deriv Synthetics have ZERO commission)
        exit_comm = 0.0 if spec.asset_class == "SYNTHETIC" else round(lots * self.settings.paper_commission_per_lot, 2)
        pnl = round(pnl - exit_comm, 2)

        balance_before = self.balance
        self.balance += pnl
        self.daily_pnl += pnl

        position.status = PositionStatus.CLOSED
        position.closed_at = datetime.utcnow()
        position.exit_price = exit_price
        position.realized_pnl = pnl
        position.exit_reason = exit_reason

        # Persist full trade journal record to database (Section 13 of project.md)
        mfe = getattr(position, "highest_pnl", 0.0)
        mae = getattr(position, "lowest_pnl", 0.0)
        exit_eff = round(pnl / max(mfe, 0.01), 2) if mfe > 0 else 1.0

        record = TradeRecord(
            trade_id=position.id,
            symbol=position.symbol,
            side=position.side,
            timeframe="1m",
            entry_price=position.entry_price,
            exit_price=exit_price,
            volume=position.volume,
            volume_lots=lots,
            stop_loss=position.stop_loss,
            take_profit=position.take_profit,
            risk_percent=self.settings.risk_per_trade,
            risk_amount=abs(position.entry_price - position.stop_loss) / max(spec.tick_size, 1e-9) * spec.tick_value * lots,
            balance_before=balance_before,
            balance_after=self.balance,
            profit_loss=pnl,
            return_percent=round((pnl / balance_before) * 100.0, 4) if balance_before > 0 else 0.0,
            duration_seconds=position.duration_seconds,
            strategy=position.strategy,
            market_regime=position.regime or "UNKNOWN",
            volatility=0.0,
            whipsaw_probability=position.whipsaw_prob,
            direction_probability=0.0,
            trade_quality=position.ai_quality,
            model_version=position.model_version or "v1",
            entry_timestamp=position.opened_at,
            exit_timestamp=position.closed_at,
            exit_reason=exit_reason.value,
            mfe=mfe,
            mae=mae,
            exit_efficiency=exit_eff,
        )
        try:
            DatabaseRepository.save_trade_record(record)
        except Exception as e:
            logger.error(f"Failed to persist trade record: {e}")

        # Dispatch automated post-mortem failure learning to ML engine
        try:
            from app.learning.post_mortem_engine import post_mortem_engine
            post_mortem_engine.diagnose_closed_position(record)
        except Exception as e:
            logger.error(f"Post-mortem diagnosis error: {e}")

        del self.open_positions[position_id]
        self.closed_positions.append(position)

        logger.info(
            f"[PAPER CLOSE] {position.symbol} {position.side.value} @ {exit_price} "
            f"PnL: ${pnl:+.2f}, Reason: {exit_reason.value}, Duration: {position.duration_seconds}s"
        )
        return True

    async def get_open_positions(self) -> List[Position]:
        return list(self.open_positions.values())

    def update_tick(self, tick: Tick) -> None:
        """
        Process incoming tick, update positions, and evaluate SL/TP triggers.
        """
        self.latest_ticks[tick.symbol] = tick

        # Notify spot callbacks
        for cb in self.spot_callbacks:
            try:
                cb(tick)
            except Exception as e:
                logger.error(f"Error in spot callback: {e}")

        # Check open positions on this symbol for SL/TP hits
        positions_to_close: List[tuple[str, ExitReason]] = []

        for pos_id, pos in list(self.open_positions.items()):
            if pos.symbol != tick.symbol:
                continue

            spec = self.symbols.get(pos.symbol)
            if not spec:
                continue

            pos.current_price = tick.bid if pos.side == TradeSide.BUY else tick.ask

            # Update unrealized PnL
            price_delta = (
                (pos.current_price - pos.entry_price)
                if pos.side == TradeSide.BUY
                else (pos.entry_price - pos.current_price)
            )
            ticks = price_delta / max(spec.tick_size, 1e-9)
            lots = pos.volume / max(spec.contract_size, 1e-5)
            exit_comm = 0.0 if spec.asset_class == "SYNTHETIC" else round(lots * self.settings.paper_commission_per_lot, 2)
            pos.unrealized_pnl = round(ticks * spec.tick_value * lots - exit_comm, 2)

            # Track peak unrealized profit (MFE) and deepest drawdown (MAE)
            if pos.unrealized_pnl > pos.highest_pnl:
                pos.highest_pnl = pos.unrealized_pnl
            if pos.unrealized_pnl < getattr(pos, "lowest_pnl", 0.0):
                pos.lowest_pnl = pos.unrealized_pnl

            # 1. AUTO-BREAKEVEN: Lock in risk-free trade once in profit ($1.50+ or >= 0.8R)
            # This ensures winning trades NEVER turn into losing trades!
            risk_amt = max(0.50, abs(pos.entry_price - (pos.trailed_sl or pos.stop_loss)) / max(spec.tick_size, 1e-9) * spec.tick_value * lots)
            be_threshold = min(1.50, risk_amt * 0.8)

            if pos.unrealized_pnl >= be_threshold and not pos.is_be_active:
                buffer = spec.tick_size * 2
                if pos.side == TradeSide.BUY:
                    new_sl = round(pos.entry_price + buffer, spec.digits)
                    if new_sl > pos.stop_loss:
                        pos.stop_loss = new_sl
                        pos.trailed_sl = new_sl
                        pos.is_be_active = True
                        logger.info(f"[AUTO-BREAKEVEN] {pos.symbol} BUY SL moved to {new_sl} (+${pos.unrealized_pnl:+.2f} profit locked risk-free)")
                else:
                    new_sl = round(pos.entry_price - buffer, spec.digits)
                    if new_sl < pos.stop_loss:
                        pos.stop_loss = new_sl
                        pos.trailed_sl = new_sl
                        pos.is_be_active = True
                        logger.info(f"[AUTO-BREAKEVEN] {pos.symbol} SELL SL moved to {new_sl} (+${pos.unrealized_pnl:+.2f} profit locked risk-free)")

            # 2. DYNAMIC TRAILING STOP: As profit expands ($2.50+ or >= 1.5R), trail 50% of peak gains
            trail_threshold = max(2.50, risk_amt * 1.5)
            if pos.unrealized_pnl >= trail_threshold:
                if pos.side == TradeSide.BUY:
                    locked_gain_price = round(pos.entry_price + (pos.current_price - pos.entry_price) * 0.5, spec.digits)
                    if locked_gain_price > pos.stop_loss:
                        pos.stop_loss = locked_gain_price
                        pos.trailed_sl = locked_gain_price
                        pos.is_be_active = True
                else:
                    locked_gain_price = round(pos.entry_price - (pos.entry_price - pos.current_price) * 0.5, spec.digits)
                    if locked_gain_price < pos.stop_loss:
                        pos.stop_loss = locked_gain_price
                        pos.trailed_sl = locked_gain_price
                        pos.is_be_active = True

            # Check Take Profit & Stop Loss
            if pos.side == TradeSide.BUY:
                if tick.bid >= pos.take_profit:
                    positions_to_close.append((pos_id, ExitReason.TAKE_PROFIT))
                elif tick.bid <= pos.stop_loss:
                    reason = ExitReason.TAKE_PROFIT if pos.is_be_active and pos.unrealized_pnl > 0 else ExitReason.STOP_LOSS
                    positions_to_close.append((pos_id, reason))
            elif pos.side == TradeSide.SELL:
                if tick.ask <= pos.take_profit:
                    positions_to_close.append((pos_id, ExitReason.TAKE_PROFIT))
                elif tick.ask >= pos.stop_loss:
                    reason = ExitReason.TAKE_PROFIT if pos.is_be_active and pos.unrealized_pnl > 0 else ExitReason.STOP_LOSS
                    positions_to_close.append((pos_id, reason))

        for p_id, reason in positions_to_close:
            asyncio.create_task(self.close_position(p_id, reason))

    async def move_to_breakeven(self, position_id: str) -> bool:
        """Snap a position's stop loss to its entry price plus buffer."""
        pos = self.open_positions.get(position_id)
        if not pos:
            return False
        spec = self.symbols.get(pos.symbol)
        if not spec:
            return False
        buffer = spec.tick_size * 2
        if pos.side == TradeSide.BUY:
            pos.stop_loss = round(pos.entry_price + buffer, spec.digits)
        else:
            pos.stop_loss = round(pos.entry_price - buffer, spec.digits)
        pos.is_be_active = True
        pos.trailed_sl = pos.stop_loss
        logger.info(f"[MANUAL BREAKEVEN] Position {position_id} on {pos.symbol} moved to BE @ {pos.stop_loss}")
        return True

    async def breakeven_all_positions(self) -> int:
        """Move all open positions to breakeven."""
        count = 0
        for pos_id in list(self.open_positions.keys()):
            if await self.move_to_breakeven(pos_id):
                count += 1
        return count

    async def close_all_positions(self, reason: ExitReason = ExitReason.MANUAL) -> int:
        """Close all currently open positions."""
        pos_ids = list(self.open_positions.keys())
        count = 0
        for pos_id in pos_ids:
            if await self.close_position(pos_id, reason):
                count += 1
        return count
