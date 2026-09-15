"""
Account-Tier Sizing & Small Account Feasibility Engine.
Classifies accounts into mathematical risk tiers (MICRO, SMALL, MEDIUM, INSTITUTIONAL),
computes minimum viable stop loss dollar risk, and pre-filters instruments to protect small accounts.
"""

from typing import Tuple, List, Optional, Dict
from pydantic import BaseModel
from loguru import logger

from app.broker.models import SymbolSpecification
from app.market.deriv_universe import (
    AccountTier,
    DERIV_UNIVERSE_CATALOG,
    DerivInstrumentMetadata,
    DerivUniverseRegistry,
)


class FeasibilityVerdict(BaseModel):
    symbol: str
    is_safe: bool
    account_tier: AccountTier
    required_tier: AccountTier
    min_dollar_risk: float
    max_risk_allowed: float
    risk_percentage_of_account: float
    veto_reason: Optional[str] = None
    recommended_alternatives: List[str] = []


class AccountTierEngine:
    """
    Evaluates account balance feasibility to strictly prevent beginner/small account blowouts.
    """

    @staticmethod
    def classify_account(balance: float) -> AccountTier:
        """Categorize account into quantitative equity tiers."""
        if balance < 100.0:
            return AccountTier.MICRO
        elif balance < 500.0:
            return AccountTier.SMALL
        elif balance < 2500.0:
            return AccountTier.MEDIUM
        else:
            return AccountTier.INSTITUTIONAL

    @classmethod
    def calculate_minimum_dollar_risk(
        cls, spec: SymbolSpecification, sl_distance_points: Optional[float] = None
    ) -> float:
        """
        Calculate the absolute minimum dollar loss if a trade at minimum lot size hits its stop loss.
        """
        meta = DerivUniverseRegistry.get_metadata(spec.symbol)
        typical_sl = (
            sl_distance_points
            if sl_distance_points is not None and sl_distance_points > 0
            else (meta.typical_atr_points * 1.5 if meta else spec.tick_size * 50)
        )

        tick_size = max(spec.tick_size, 1e-9)
        ticks_at_risk = typical_sl / tick_size
        cost_per_lot = ticks_at_risk * max(spec.tick_value, 1e-5)
        min_dollar_risk = spec.lot_min * cost_per_lot
        return round(min_dollar_risk, 2)

    @classmethod
    def evaluate_symbol_feasibility(
        cls,
        spec: SymbolSpecification,
        balance: float,
        max_risk_percent: float = 0.02,
        sl_distance_points: Optional[float] = None,
    ) -> FeasibilityVerdict:
        """
        Check if an account balance can mathematically trade this symbol within risk parameters.
        """
        account_tier = cls.classify_account(balance)
        max_risk_allowed = balance * max_risk_percent
        min_dollar_risk = cls.calculate_minimum_dollar_risk(spec, sl_distance_points)
        risk_pct = (min_dollar_risk / max(balance, 1.0)) * 100.0

        meta = DerivUniverseRegistry.get_metadata(spec.symbol)
        required_tier = meta.tier if meta else AccountTier.MEDIUM

        tier_hierarchy = {
            AccountTier.MICRO: 1,
            AccountTier.SMALL: 2,
            AccountTier.MEDIUM: 3,
            AccountTier.INSTITUTIONAL: 4,
        }

        # Check 1: Minimum dollar risk vs max allowed risk
        is_safe = True
        veto_reason = None
        alternatives = []

        if min_dollar_risk > max_risk_allowed * 1.25:  # Allow 25% boundary tolerance
            is_safe = False
            veto_reason = (
                f"[BLOWOUT RISK VETO] {spec.symbol} minimum risk (${min_dollar_risk:.2f}, {risk_pct:.1f}% of balance) "
                f"exceeds max 2% risk budget (${max_risk_allowed:.2f}) on a ${balance:.2f} [{account_tier.value}] account."
            )
            # Recommend safe alternatives in same or related asset class
            if spec.asset_class == "SYNTHETIC":
                alternatives = ["Vol_10_1s", "Vol_25_1s", "Step_Index", "Vol_15_1s"]
            elif spec.asset_class in ("METALS", "FOREX"):
                alternatives = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]
            else:
                alternatives = ["Vol_10_1s", "EURUSD"]

        elif tier_hierarchy[account_tier] < tier_hierarchy[required_tier]:
            is_safe = False
            veto_reason = (
                f"[TIER MISMATCH] {spec.symbol} requires [{required_tier.value}] tier, "
                f"but current account is [{account_tier.value}] (${balance:.2f})."
            )
            alternatives = [
                s.symbol for s in DerivUniverseRegistry.get_symbols_by_tier(account_tier)[:4]
            ]

        return FeasibilityVerdict(
            symbol=spec.symbol,
            is_safe=is_safe,
            account_tier=account_tier,
            required_tier=required_tier,
            min_dollar_risk=min_dollar_risk,
            max_risk_allowed=round(max_risk_allowed, 2),
            risk_percentage_of_account=round(risk_pct, 1),
            veto_reason=veto_reason,
            recommended_alternatives=alternatives,
        )

    @classmethod
    def filter_scannable_symbols(
        cls, symbols: List[SymbolSpecification], balance: float, max_risk_percent: float = 0.02
    ) -> List[SymbolSpecification]:
        """
        Pre-filter universe so that scanner only analyzes symbols that the account can legally trade.
        """
        approved = []
        for s in symbols:
            verdict = cls.evaluate_symbol_feasibility(s, balance, max_risk_percent)
            if verdict.is_safe:
                approved.append(s)
            else:
                logger.debug(f"Pre-scan filter: {verdict.veto_reason}")
        return approved
