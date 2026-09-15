"""
Abstract Broker Adapter Interface.
Ensures the trading engine is completely broker-agnostic (project.md Section 3.2).
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Callable, Dict, Any

from app.broker.models import (
    AccountInfo,
    SymbolSpecification,
    Tick,
    Candle,
    Order,
    Position,
    TradeSide,
    ExitReason,
)


class BrokerAdapter(ABC):
    """Abstract interface representing a broker gateway connection."""

    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection with the broker."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Safely terminate connection with the broker."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if broker connection is active."""
        pass

    @abstractmethod
    async def get_account_info(self) -> AccountInfo:
        """Retrieve latest account balance, equity, and margin."""
        pass

    @abstractmethod
    async def get_symbols(self) -> List[SymbolSpecification]:
        """Discover available trading instruments and contract specifications."""
        pass

    @abstractmethod
    async def subscribe_spots(
        self, symbols: List[str], callback: Callable[[Tick], None]
    ) -> None:
        """Subscribe to real-time spot prices."""
        pass

    @abstractmethod
    async def get_historical_candles(
        self, symbol: str, timeframe: str, count: int = 500
    ) -> List[Candle]:
        """Fetch historical candlestick data."""
        pass

    @abstractmethod
    async def send_market_order(
        self,
        symbol: str,
        side: TradeSide,
        volume_lots: float,
        stop_loss: float,
        take_profit: float,
        comment: str = "",
    ) -> Order:
        """Submit a new market execution order."""
        pass

    @abstractmethod
    async def close_position(
        self, position_id: str, exit_reason: ExitReason
    ) -> bool:
        """Close an active position."""
        pass

    @abstractmethod
    async def get_open_positions(self) -> List[Position]:
        """Retrieve all currently open positions."""
        pass
