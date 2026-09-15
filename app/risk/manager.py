"""
Master Risk Engine: Absolute Veto Authority over AI.
Section 28, 73, and 102 of project.md.
"""

from typing import List, Optional
from datetime import datetime
from loguru import logger

from app.config.settings import Settings, get_settings
from app.broker.models import (
    TradeSignal,
    AIDecisionObject,
    RiskDecisionObject,
    AccountInfo,
    SymbolSpecification,
    Position,
    Tick,
)
from app.risk.lot_calculator import LotCalculator
from app.risk.exposure import ExposureManager
from app.risk.correlation import CorrelationManager
from app.risk.validators import TradeValidators
from app.risk.var import ValueAtRiskEngine
from app.risk.volatility_targeting import VolatilityTargetingEngine
from app.risk.covariance import CovarianceEngine
from app.fundamental.blackout import NewsBlackoutShield
from app.database.repository import DatabaseRepository


class RiskEngine:
    """
    Deterministic risk gatekeeper. Evaluates every setup and has absolute veto power.
    Institutional-grade risk architecture integrating VaR, Volatility Targeting, and Macro Shields.
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.lot_calculator = LotCalculator()
        self.exposure_manager = ExposureManager(
            max_open_positions=self.settings.max_open_positions,
            max_portfolio_risk_pct=self.settings.max_daily_loss,
        )
        self.correlation_manager = CorrelationManager(max_cluster_positions=1)
        self.var_engine = ValueAtRiskEngine()
        self.vol_targeting = VolatilityTargetingEngine()
        self.covariance_engine = CovarianceEngine()
        self.blackout_shield = NewsBlackoutShield()
        self.peak_balance: float = 0.0

    def evaluate_trade(
        self,
        signal: TradeSignal,
        ai_decision: AIDecisionObject,
        account: AccountInfo,
        spec: SymbolSpecification,
        current_tick: Tick,
        open_positions: List[Position],
    ) -> RiskDecisionObject:
        """
        Validate proposed trade setup against all deterministic risk rules.
        """
        now = datetime.utcnow()
        if account.balance > self.peak_balance:
            self.peak_balance = account.balance

        # Helper to construct rejection
        def veto(reason: str) -> RiskDecisionObject:
            logger.warning(f"[RISK VETO] {signal.symbol} rejected: {reason}")
            try:
                DatabaseRepository.log_risk_event(signal.symbol, "VETO", reason)
            except Exception:
                pass
            return RiskDecisionObject(
                approved=False,
                symbol=signal.symbol,
                side=signal.side,
                veto_reason=reason,
                timestamp=now,
            )

        # 1. Macro News Blackout Shield (Spread blowout & slippage protection)
        is_blackout, blackout_reason = self.blackout_shield.check_blackout(signal.symbol)
        if is_blackout and blackout_reason:
            return veto(blackout_reason)

        # 2. Validate Account-Level Risk (Daily loss & drawdown)
        dl_err = TradeValidators.validate_daily_loss(account, self.settings.max_daily_loss)
        if dl_err:
            return veto(dl_err)

        dd_err = TradeValidators.validate_drawdown(
            account.equity, self.peak_balance, self.settings.max_drawdown
        )
        if dd_err:
            return veto(dd_err)

        # 3. Validate Spread
        spread_err = TradeValidators.validate_spread(
            current_tick, spec, self.settings.max_spread_pips
        )
        if spread_err:
            return veto(spread_err)

        # 4. Validate AI Quality & Thresholds
        ai_err = TradeValidators.validate_ai_decision(
            ai_decision,
            min_win_prob=self.settings.min_direction_probability,
            min_quality=self.settings.min_trade_quality,
            max_whipsaw=self.settings.max_whipsaw_probability,
            min_rr=self.settings.min_risk_reward,
        )
        if ai_err:
            return veto(ai_err)

        # 5. Validate Portfolio Exposure & Duplication
        exp_err = self.exposure_manager.check_exposure(
            signal.symbol, open_positions, self.settings.risk_per_trade
        )
        if exp_err:
            return veto(exp_err)

        # 6. Validate Correlation Exposure
        corr_err = self.correlation_manager.check_correlation(
            signal.symbol, signal.side, open_positions
        )
        if corr_err:
            return veto(corr_err)

        # 6. Dynamic Lot Calculation & Margin Verification
        lots, risk_amount, margin_req, lot_err = self.lot_calculator.calculate_lot_size(
            balance=account.balance,
            risk_percent=self.settings.risk_per_trade,
            entry_price=signal.entry_price,
            stop_loss_price=signal.stop_loss,
            spec=spec,
            free_margin=account.free_margin,
        )
        if lot_err:
            return veto(lot_err)

        if lots <= 0:
            return veto("Calculated lot size is zero")

        # 7. Net Currency Delta Cap Check
        delta_err = self.covariance_engine.check_currency_delta_cap(
            signal.symbol, signal.side, lots, open_positions, max_net_currency_lots=3.0
        )
        if delta_err:
            return veto(delta_err)

        logger.info(
            f"[RISK APPROVED] {signal.symbol} {signal.side.value} Lots: {lots}, "
            f"Risk: ${risk_amount:.2f} ({self.settings.risk_per_trade*100:.2f}%), Margin: ${margin_req:.2f}"
        )

        return RiskDecisionObject(
            approved=True,
            symbol=signal.symbol,
            side=signal.side,
            risk_percent=self.settings.risk_per_trade,
            risk_amount=risk_amount,
            entry=signal.entry_price,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            volume=lots * spec.contract_size,
            volume_lots=lots,
            margin_required=margin_req,
            max_loss=risk_amount,
            veto_reason=None,
            timestamp=now,
        )
