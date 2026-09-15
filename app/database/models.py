"""
SQLAlchemy ORM models for SQLite database.
Matches tables defined in project.md Section 12.
"""

from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    DateTime,
    Boolean,
    Text,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class MarketModel(Base):
    __tablename__ = "markets"

    symbol = Column(String(32), primary_key=True)
    symbol_id = Column(Integer, nullable=True)
    description = Column(String(128), default="")
    asset_class = Column(String(32), default="FOREX")
    digits = Column(Integer, default=5)
    lot_min = Column(Float, default=0.01)
    lot_max = Column(Float, default=100.0)
    lot_step = Column(Float, default=0.01)
    contract_size = Column(Float, default=100000.0)
    tick_size = Column(Float, default=0.00001)
    tick_value = Column(Float, default=1.0)
    margin_rate = Column(Float, default=0.01)
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CandleModel(Base):
    __tablename__ = "candles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(32), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, default=0.0)

    __table_args__ = (
        Index("ix_candles_sym_tf_time", "symbol", "timeframe", "timestamp", unique=True),
    )


class FeatureModel(Base):
    __tablename__ = "features"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(32), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    feature_json = Column(Text, nullable=False)  # JSON representation of all computed features

    __table_args__ = (
        Index("ix_features_sym_time", "symbol", "timestamp", unique=True),
    )


class TradeRecordModel(Base):
    __tablename__ = "trades"

    trade_id = Column(String(64), primary_key=True)
    symbol = Column(String(32), nullable=False, index=True)
    side = Column(String(8), nullable=False)  # BUY or SELL
    timeframe = Column(String(10), default="1m")
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    volume_lots = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False)
    take_profit = Column(Float, nullable=False)
    risk_percent = Column(Float, nullable=False)
    risk_amount = Column(Float, nullable=False)
    balance_before = Column(Float, nullable=False)
    balance_after = Column(Float, nullable=False)
    profit_loss = Column(Float, nullable=False)
    return_percent = Column(Float, nullable=False)
    duration_seconds = Column(Integer, nullable=False)
    strategy = Column(String(64), nullable=False)
    market_regime = Column(String(32), default="UNKNOWN")
    volatility = Column(Float, default=0.0)
    whipsaw_probability = Column(Float, default=0.0)
    direction_probability = Column(Float, default=0.0)
    trade_quality = Column(Float, default=0.0)
    model_version = Column(String(64), default="v1")
    entry_timestamp = Column(DateTime, nullable=False, index=True)
    exit_timestamp = Column(DateTime, nullable=False, index=True)
    exit_reason = Column(String(32), nullable=False)  # TAKE_PROFIT, STOP_LOSS, STAGNATION, TIMEOUT


class AccountSnapshotModel(Base):
    __tablename__ = "account_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    balance = Column(Float, nullable=False)
    equity = Column(Float, nullable=False)
    margin_used = Column(Float, default=0.0)
    free_margin = Column(Float, default=0.0)
    daily_pnl = Column(Float, default=0.0)
    open_positions = Column(Integer, default=0)
    trading_mode = Column(String(16), default="paper")


class RiskEventModel(Base):
    __tablename__ = "risk_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    symbol = Column(String(32), nullable=False)
    event_type = Column(String(64), nullable=False)  # VETO, DAILY_LOSS_LIMIT, DRAWDOWN_LIMIT, SPREAD_REJECT
    details = Column(Text, nullable=False)


class ModelRegistryModel(Base):
    __tablename__ = "model_registry"

    model_name = Column(String(64), primary_key=True)
    version = Column(String(32), primary_key=True)
    stage = Column(String(16), default="staging")  # staging, production, archive
    file_path = Column(String(256), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    accuracy = Column(Float, nullable=True)
    profit_factor = Column(Float, nullable=True)
    win_rate = Column(Float, nullable=True)
    sharpe = Column(Float, nullable=True)
    metrics_json = Column(Text, default="{}")


class SystemLogModel(Base):
    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    level = Column(String(16), nullable=False)
    subsystem = Column(String(32), nullable=False)
    message = Column(Text, nullable=False)


class TradeMistakeModel(Base):
    __tablename__ = "trade_mistakes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    trade_id = Column(String(64), nullable=True, index=True)
    symbol = Column(String(32), nullable=False, index=True)
    agent_id = Column(Integer, nullable=True)
    mistake_type = Column(String(64), nullable=False, index=True)
    loss_amount = Column(Float, default=0.0)
    account_balance = Column(Float, default=0.0)
    risk_percent = Column(Float, default=0.0)
    details = Column(Text, nullable=False)
    feature_snapshot_json = Column(Text, default="{}")
    action_taken = Column(String(128), default="PENALTY_COOLDOWN")

