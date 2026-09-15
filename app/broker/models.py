"""
Domain models and internal data representations.
Decouples broker-specific formats from internal AI, risk, and execution logic.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class TradeSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class MarketRegime(str, Enum):
    TRENDING_UP = "TRENDING_UP"
    TRENDING_DOWN = "TRENDING_DOWN"
    RANGING = "RANGING"
    BREAKOUT = "BREAKOUT"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    LOW_VOLATILITY = "LOW_VOLATILITY"
    CHOPPY = "CHOPPY"
    UNKNOWN = "UNKNOWN"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class PositionStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class ExitReason(str, Enum):
    TAKE_PROFIT = "TAKE_PROFIT"
    STOP_LOSS = "STOP_LOSS"
    TIMEOUT = "TIMEOUT"
    STAGNATION = "STAGNATION"
    RISK_CUT = "RISK_CUT"
    RECONCILIATION = "RECONCILIATION"
    MANUAL = "MANUAL"
    EMERGENCY_STOP = "EMERGENCY_STOP"
    SIGNAL = "SIGNAL"


class Tick(BaseModel):
    symbol: str
    bid: float
    ask: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2.0

    @property
    def spread(self) -> float:
        return self.ask - self.bid


class Candle(BaseModel):
    symbol: str
    timeframe: str  # e.g., "1m", "5m", "15m", "1h"
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0

    @property
    def is_bullish(self) -> bool:
        return self.close > self.open

    @property
    def is_bearish(self) -> bool:
        return self.close < self.open

    @property
    def body_size(self) -> float:
        return abs(self.close - self.open)

    @property
    def total_range(self) -> float:
        return max(self.high - self.low, 1e-9)

    @property
    def upper_wick(self) -> float:
        return self.high - max(self.open, self.close)

    @property
    def lower_wick(self) -> float:
        return min(self.open, self.close) - self.low


class SymbolSpecification(BaseModel):
    symbol: str
    symbol_id: Optional[int] = None
    description: str = ""
    asset_class: str = "FOREX"  # "FOREX", "METALS", "CRYPTO", "SYNTHETIC", "INDICES"
    digits: int = 5
    lot_min: float = 0.01
    lot_max: float = 100.0
    lot_step: float = 0.01
    contract_size: float = 100000.0
    tick_size: float = 0.00001
    tick_value: float = 1.0  # Value of 1 tick for 1 lot in account currency
    margin_rate: float = 0.01  # 1% = 1:100 leverage


class AccountInfo(BaseModel):
    account_id: str
    broker: str
    currency: str = "USD"
    balance: float
    equity: float
    margin_used: float = 0.0
    free_margin: float = 0.0
    margin_level: Optional[float] = None
    daily_pnl: float = 0.0
    open_positions_count: int = 0
    is_live: bool = False


class TradeSignal(BaseModel):
    symbol: str
    side: TradeSide
    strategy: str
    timeframe: str
    entry_price: float
    stop_loss: float
    take_profit: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AIDecisionObject(BaseModel):
    """Normalized AI Output as defined in project.md Section 72 and strategy.md."""
    symbol: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    direction: Optional[TradeSide] = None  # BUY, SELL, or None for NO TRADE
    buy_probability: float = 0.0
    sell_probability: float = 0.0
    no_trade_probability: float = 1.0
    trade_quality: float = 0.0
    regime: MarketRegime = MarketRegime.UNKNOWN
    regime_confidence: float = 0.0
    whipsaw_probability: float = 0.0
    expected_duration_seconds: int = 60
    expected_rr: float = 1.5
    strategy: str = ""
    model_version: str = "v2_continuation"
    raw_scores: Dict[str, float] = Field(default_factory=dict)
    # V2 Architecture additions (strategy.md & project.md)
    momentum_score: float = 50.0
    momentum_state: str = "BUILDING"
    volume_pressure: float = 1.0
    volume_state: str = "CONFIRMING"
    continuation_probability: float = 0.50
    lifecycle_action: str = "ENTER"


class RiskDecisionObject(BaseModel):
    """Risk Engine Output as defined in project.md Section 73."""
    approved: bool
    symbol: str
    side: Optional[TradeSide] = None
    risk_percent: float = 0.0
    risk_amount: float = 0.0
    entry: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    volume: float = 0.0  # Normalized volume
    volume_lots: float = 0.0  # Lots
    margin_required: float = 0.0
    max_loss: float = 0.0
    veto_reason: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Order(BaseModel):
    id: str
    broker_order_id: Optional[str] = None
    symbol: str
    side: TradeSide
    order_type: OrderType = OrderType.MARKET
    volume: float
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    filled_at: Optional[datetime] = None
    fill_price: Optional[float] = None
    rejection_reason: Optional[str] = None


class Position(BaseModel):
    id: str
    broker_position_id: Optional[str] = None
    symbol: str
    side: TradeSide
    volume: float
    entry_price: float
    current_price: float
    stop_loss: float
    take_profit: float
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    status: PositionStatus = PositionStatus.OPEN
    opened_at: datetime = Field(default_factory=datetime.utcnow)
    closed_at: Optional[datetime] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[ExitReason] = None
    strategy: str = ""
    model_version: str = ""
    ai_quality: float = 0.0
    whipsaw_prob: float = 0.0
    regime: str = ""
    is_be_active: bool = False
    highest_pnl: float = 0.0
    lowest_pnl: float = 0.0
    trailed_sl: Optional[float] = None
    # V2 Continuation & Lifecycle monitoring fields
    momentum_score: float = 50.0
    volume_rvol: float = 1.0
    continuation_prob: float = 0.50
    lifecycle_action: str = "HOLD"

    @property
    def duration_seconds(self) -> int:
        end = self.closed_at or datetime.utcnow()
        return max(0, int((end - self.opened_at).total_seconds()))


class TradeRecord(BaseModel):
    """Complete Trade Lifecycle Record as defined in project.md Section 13."""
    trade_id: str
    symbol: str
    side: TradeSide
    timeframe: str = "1m"
    entry_price: float
    exit_price: float
    volume: float = 1000.0
    volume_lots: float
    stop_loss: float = 0.0
    take_profit: float = 0.0
    risk_percent: float = 0.01
    risk_amount: float = 10.0
    balance_before: float
    balance_after: float
    profit_loss: float
    return_percent: float
    duration_seconds: int
    strategy: str
    market_regime: str = "UNKNOWN"
    volatility: float = 0.0
    whipsaw_probability: float = 0.0
    direction_probability: float = 0.0
    trade_quality: float = 0.0
    model_version: str = "v1"
    entry_timestamp: datetime
    exit_timestamp: datetime
    exit_reason: str
    mfe: float = 0.0
    mae: float = 0.0
    exit_efficiency: float = 0.0
