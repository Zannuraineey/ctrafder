"""
Database repository for persistence and query operations.
"""

import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.database.session import get_db_session
from app.database.models import (
    MarketModel,
    CandleModel,
    FeatureModel,
    TradeRecordModel,
    AccountSnapshotModel,
    RiskEventModel,
    ModelRegistryModel,
    TradeMistakeModel,
)
from app.broker.models import Candle, SymbolSpecification, TradeRecord, AccountInfo


class DatabaseRepository:
    """Repository handling all transactional queries for trading engine."""

    # ---------------- Markets ----------------
    @staticmethod
    def save_market(spec: SymbolSpecification) -> None:
        with get_db_session() as session:
            existing = session.query(MarketModel).filter_by(symbol=spec.symbol).first()
            if existing:
                existing.symbol_id = spec.symbol_id
                existing.description = spec.description
                existing.asset_class = spec.asset_class
                existing.digits = spec.digits
                existing.lot_min = spec.lot_min
                existing.lot_max = spec.lot_max
                existing.lot_step = spec.lot_step
                existing.contract_size = spec.contract_size
                existing.tick_size = spec.tick_size
                existing.tick_value = spec.tick_value
                existing.margin_rate = spec.margin_rate
                existing.updated_at = datetime.utcnow()
            else:
                market = MarketModel(
                    symbol=spec.symbol,
                    symbol_id=spec.symbol_id,
                    description=spec.description,
                    asset_class=spec.asset_class,
                    digits=spec.digits,
                    lot_min=spec.lot_min,
                    lot_max=spec.lot_max,
                    lot_step=spec.lot_step,
                    contract_size=spec.contract_size,
                    tick_size=spec.tick_size,
                    tick_value=spec.tick_value,
                    margin_rate=spec.margin_rate,
                )
                session.add(market)

    @staticmethod
    def get_market(symbol: str) -> Optional[SymbolSpecification]:
        with get_db_session() as session:
            record = session.query(MarketModel).filter_by(symbol=symbol).first()
            if not record:
                return None
            return SymbolSpecification(
                symbol=record.symbol,
                symbol_id=record.symbol_id,
                description=record.description,
                asset_class=record.asset_class,
                digits=record.digits,
                lot_min=record.lot_min,
                lot_max=record.lot_max,
                lot_step=record.lot_step,
                contract_size=record.contract_size,
                tick_size=record.tick_size,
                tick_value=record.tick_value,
                margin_rate=record.margin_rate,
            )

    @staticmethod
    def get_all_active_markets() -> List[SymbolSpecification]:
        with get_db_session() as session:
            records = session.query(MarketModel).filter_by(is_active=True).all()
            return [
                SymbolSpecification(
                    symbol=r.symbol,
                    symbol_id=r.symbol_id,
                    description=r.description,
                    asset_class=r.asset_class,
                    digits=r.digits,
                    lot_min=r.lot_min,
                    lot_max=r.lot_max,
                    lot_step=r.lot_step,
                    contract_size=r.contract_size,
                    tick_size=r.tick_size,
                    tick_value=r.tick_value,
                    margin_rate=r.margin_rate,
                )
                for r in records
            ]

    # ---------------- Candles ----------------
    @staticmethod
    def save_candles_bulk(candles: List[Candle]) -> None:
        if not candles:
            return
        with get_db_session() as session:
            for c in candles:
                existing = (
                    session.query(CandleModel)
                    .filter_by(symbol=c.symbol, timeframe=c.timeframe, timestamp=c.timestamp)
                    .first()
                )
                if existing:
                    existing.open = c.open
                    existing.high = c.high
                    existing.low = c.low
                    existing.close = c.close
                    existing.volume = c.volume
                else:
                    session.add(
                        CandleModel(
                            symbol=c.symbol,
                            timeframe=c.timeframe,
                            timestamp=c.timestamp,
                            open=c.open,
                            high=c.high,
                            low=c.low,
                            close=c.close,
                            volume=c.volume,
                        )
                    )

    @staticmethod
    def get_recent_candles(
        symbol: str, timeframe: str = "1m", limit: int = 500
    ) -> List[Candle]:
        with get_db_session() as session:
            records = (
                session.query(CandleModel)
                .filter_by(symbol=symbol, timeframe=timeframe)
                .order_by(desc(CandleModel.timestamp))
                .limit(limit)
                .all()
            )
            # Return in chronological order
            records.reverse()
            return [
                Candle(
                    symbol=r.symbol,
                    timeframe=r.timeframe,
                    timestamp=r.timestamp,
                    open=r.open,
                    high=r.high,
                    low=r.low,
                    close=r.close,
                    volume=r.volume,
                )
                for r in records
            ]

    # ---------------- Trades ----------------
    @staticmethod
    def save_trade_record(trade: TradeRecord) -> None:
        with get_db_session() as session:
            record = TradeRecordModel(
                trade_id=trade.trade_id,
                symbol=trade.symbol,
                side=trade.side.value if hasattr(trade.side, "value") else str(trade.side),
                timeframe=trade.timeframe,
                entry_price=trade.entry_price,
                exit_price=trade.exit_price,
                volume=trade.volume,
                volume_lots=trade.volume_lots,
                stop_loss=trade.stop_loss,
                take_profit=trade.take_profit,
                risk_percent=trade.risk_percent,
                risk_amount=trade.risk_amount,
                balance_before=trade.balance_before,
                balance_after=trade.balance_after,
                profit_loss=trade.profit_loss,
                return_percent=trade.return_percent,
                duration_seconds=trade.duration_seconds,
                strategy=trade.strategy,
                market_regime=trade.market_regime,
                volatility=trade.volatility,
                whipsaw_probability=trade.whipsaw_probability,
                direction_probability=trade.direction_probability,
                trade_quality=trade.trade_quality,
                model_version=trade.model_version,
                entry_timestamp=trade.entry_timestamp,
                exit_timestamp=trade.exit_timestamp,
                exit_reason=trade.exit_reason,
            )
            session.merge(record)

    @staticmethod
    def get_recent_trades(limit: int = 50) -> List[Dict[str, Any]]:
        with get_db_session() as session:
            trades = (
                session.query(TradeRecordModel)
                .order_by(desc(TradeRecordModel.exit_timestamp))
                .limit(limit)
                .all()
            )
            return [
                {
                    "trade_id": t.trade_id,
                    "symbol": t.symbol,
                    "side": t.side,
                    "entry_price": t.entry_price,
                    "exit_price": t.exit_price,
                    "volume_lots": t.volume_lots,
                    "profit_loss": t.profit_loss,
                    "return_percent": t.return_percent,
                    "duration_seconds": t.duration_seconds,
                    "strategy": t.strategy,
                    "exit_reason": t.exit_reason,
                    "entry_timestamp": t.entry_timestamp,
                    "exit_timestamp": t.exit_timestamp,
                }
                for t in trades
            ]

    @staticmethod
    def get_trade_stats() -> Dict[str, Any]:
        with get_db_session() as session:
            total_trades = session.query(func.count(TradeRecordModel.trade_id)).scalar() or 0
            if total_trades == 0:
                return {
                    "total_trades": 0,
                    "win_rate": 0.0,
                    "profit_factor": 0.0,
                    "total_pnl": 0.0,
                    "avg_duration": 0,
                }

            wins = (
                session.query(func.count(TradeRecordModel.trade_id))
                .filter(TradeRecordModel.profit_loss > 0)
                .scalar()
                or 0
            )
            losses = (
                session.query(func.count(TradeRecordModel.trade_id))
                .filter(TradeRecordModel.profit_loss < 0)
                .scalar()
                or 0
            )
            total_pnl = (
                session.query(func.sum(TradeRecordModel.profit_loss)).scalar() or 0.0
            )
            gross_profit = (
                session.query(func.sum(TradeRecordModel.profit_loss))
                .filter(TradeRecordModel.profit_loss > 0)
                .scalar()
                or 0.0
            )
            gross_loss = abs(
                session.query(func.sum(TradeRecordModel.profit_loss))
                .filter(TradeRecordModel.profit_loss < 0)
                .scalar()
                or 0.0
            )
            profit_factor = (
                (gross_profit / gross_loss) if gross_loss > 0 else (999.0 if gross_profit > 0 else 0.0)
            )
            avg_duration = (
                session.query(func.avg(TradeRecordModel.duration_seconds)).scalar() or 0
            )

            return {
                "total_trades": total_trades,
                "wins": wins,
                "losses": losses,
                "win_rate": round(wins / total_trades, 4) if total_trades > 0 else 0.0,
                "profit_factor": round(profit_factor, 2),
                "total_pnl": round(total_pnl, 2),
                "avg_duration": int(avg_duration),
            }

    # ---------------- Snapshots ----------------
    @staticmethod
    def save_account_snapshot(account: AccountInfo, trading_mode: str = "paper") -> None:
        with get_db_session() as session:
            snapshot = AccountSnapshotModel(
                balance=account.balance,
                equity=account.equity,
                margin_used=account.margin_used,
                free_margin=account.free_margin,
                daily_pnl=account.daily_pnl,
                open_positions=account.open_positions_count,
                trading_mode=trading_mode,
            )
            session.add(snapshot)

    # ---------------- Risk Events ----------------
    @staticmethod
    def log_risk_event(symbol: str, event_type: str, details: str) -> None:
        with get_db_session() as session:
            event = RiskEventModel(
                symbol=symbol,
                event_type=event_type,
                details=details,
            )
            session.add(event)

    # ---------------- Trade Mistakes & Anti-Greed Diagnostics ----------------
    @staticmethod
    def save_trade_mistake(
        symbol: str,
        mistake_type: str,
        details: str,
        trade_id: Optional[str] = None,
        agent_id: Optional[int] = None,
        loss_amount: float = 0.0,
        account_balance: float = 0.0,
        risk_percent: float = 0.0,
        feature_snapshot: Optional[Dict[str, Any]] = None,
        action_taken: str = "PENALTY_COOLDOWN",
    ) -> None:
        with get_db_session() as session:
            mistake = TradeMistakeModel(
                trade_id=trade_id,
                symbol=symbol,
                agent_id=agent_id,
                mistake_type=mistake_type,
                loss_amount=loss_amount,
                account_balance=account_balance,
                risk_percent=risk_percent,
                details=details,
                feature_snapshot_json=json.dumps(feature_snapshot or {}),
                action_taken=action_taken,
            )
            session.add(mistake)

    @staticmethod
    def get_recent_mistakes(limit: int = 50) -> List[Dict[str, Any]]:
        with get_db_session() as session:
            mistakes = (
                session.query(TradeMistakeModel)
                .order_by(desc(TradeMistakeModel.timestamp))
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": m.id,
                    "timestamp": m.timestamp,
                    "trade_id": m.trade_id,
                    "symbol": m.symbol,
                    "agent_id": m.agent_id,
                    "mistake_type": m.mistake_type,
                    "loss_amount": m.loss_amount,
                    "account_balance": m.account_balance,
                    "risk_percent": m.risk_percent,
                    "details": m.details,
                    "action_taken": m.action_taken,
                    "feature_snapshot": json.loads(m.feature_snapshot_json or "{}"),
                }
                for m in mistakes
            ]

    @staticmethod
    def get_mistakes_summary() -> Dict[str, Any]:
        with get_db_session() as session:
            total_mistakes = session.query(func.count(TradeMistakeModel.id)).scalar() or 0
            total_prevented_loss = (
                session.query(func.sum(TradeMistakeModel.loss_amount)).scalar() or 0.0
            )

            # Group by type
            counts = (
                session.query(TradeMistakeModel.mistake_type, func.count(TradeMistakeModel.id))
                .group_by(TradeMistakeModel.mistake_type)
                .all()
            )
            breakdown = {m_type: count for m_type, count in counts}

            return {
                "total_mistakes": total_mistakes,
                "total_loss_amount": round(total_prevented_loss, 2),
                "breakdown": breakdown,
            }

