"""
Unit tests for Deriv & cTrader Asset Universe and Account-Tier Feasibility Engine.
"""

import pytest
from app.market.deriv_universe import (
    DERIV_UNIVERSE_CATALOG,
    AccountTier,
    DerivUniverseRegistry,
)
from app.risk.account_tier import AccountTierEngine


def test_deriv_universe_catalog_completeness():
    """Verify catalog has at least 45 instruments across synthetic, forex, metals, and crypto."""
    symbols = DerivUniverseRegistry.get_all_symbols()
    assert len(symbols) >= 45

    # Check key categories are present
    synthetics = DerivUniverseRegistry.get_symbols_by_asset_class("SYNTHETIC")
    forex = DerivUniverseRegistry.get_symbols_by_asset_class("FOREX")
    metals = DerivUniverseRegistry.get_symbols_by_asset_class("METALS")

    assert len(synthetics) >= 25
    assert len(forex) >= 10
    assert len(metals) >= 4

    # Check prominent individual pairs
    assert "Vol_75" in DERIV_UNIVERSE_CATALOG
    assert "Vol_10_1s" in DERIV_UNIVERSE_CATALOG
    assert "Crash_500" in DERIV_UNIVERSE_CATALOG
    assert "Boom_1000" in DERIV_UNIVERSE_CATALOG
    assert "Step_Index" in DERIV_UNIVERSE_CATALOG
    assert "XAUUSD" in DERIV_UNIVERSE_CATALOG
    assert "EURUSD" in DERIV_UNIVERSE_CATALOG


def test_account_tier_classification():
    """Verify equity tier thresholds."""
    assert AccountTierEngine.classify_account(45.0) == AccountTier.MICRO
    assert AccountTierEngine.classify_account(99.99) == AccountTier.MICRO
    assert AccountTierEngine.classify_account(100.0) == AccountTier.SMALL
    assert AccountTierEngine.classify_account(450.0) == AccountTier.SMALL
    assert AccountTierEngine.classify_account(500.0) == AccountTier.MEDIUM
    assert AccountTierEngine.classify_account(1500.0) == AccountTier.MEDIUM
    assert AccountTierEngine.classify_account(2500.0) == AccountTier.INSTITUTIONAL
    assert AccountTierEngine.classify_account(25000.0) == AccountTier.INSTITUTIONAL


def test_small_account_feasibility_vetoes():
    """
    Verify that high-risk instruments (Vol 75, Gold) are vetoed on a $50 micro account,
    while micro-friendly pairs (Vol 10 1s, Step Index, EURUSD) are approved.
    """
    v75_spec = DERIV_UNIVERSE_CATALOG["Vol_75"].spec
    gold_spec = DERIV_UNIVERSE_CATALOG["XAUUSD"].spec
    v10_1s_spec = DERIV_UNIVERSE_CATALOG["Vol_10_1s"].spec
    step_spec = DERIV_UNIVERSE_CATALOG["Step_Index"].spec
    eurusd_spec = DERIV_UNIVERSE_CATALOG["EURUSD"].spec

    # 1. Test on $50 Micro Account
    balance_50 = 50.0

    verdict_v75 = AccountTierEngine.evaluate_symbol_feasibility(v75_spec, balance=balance_50)
    assert not verdict_v75.is_safe
    assert verdict_v75.risk_percentage_of_account > 2.5
    assert len(verdict_v75.recommended_alternatives) > 0

    verdict_gold = AccountTierEngine.evaluate_symbol_feasibility(gold_spec, balance=balance_50)
    assert not verdict_gold.is_safe
    assert verdict_gold.risk_percentage_of_account > 2.5

    verdict_v10 = AccountTierEngine.evaluate_symbol_feasibility(v10_1s_spec, balance=balance_50)
    assert verdict_v10.is_safe
    assert verdict_v10.min_dollar_risk <= 1.25

    verdict_step = AccountTierEngine.evaluate_symbol_feasibility(step_spec, balance=balance_50)
    assert verdict_step.is_safe

    verdict_eur = AccountTierEngine.evaluate_symbol_feasibility(eurusd_spec, balance=balance_50)
    assert verdict_eur.is_safe

    # 2. Test on $5000 Institutional Account (Gold & Vol 75 should be approved)
    balance_5000 = 5000.0
    verdict_gold_large = AccountTierEngine.evaluate_symbol_feasibility(gold_spec, balance=balance_5000)
    assert verdict_gold_large.is_safe

    verdict_v75_large = AccountTierEngine.evaluate_symbol_feasibility(v75_spec, balance=balance_5000)
    assert verdict_v75_large.is_safe


def test_filter_scannable_symbols():
    """Verify pre-filtering strips out dangerous pairs for a micro account."""
    all_specs = DerivUniverseRegistry.get_all_symbols()
    scannable_50 = AccountTierEngine.filter_scannable_symbols(all_specs, balance=50.0)

    symbols_50 = [s.symbol for s in scannable_50]
    assert "Vol_10_1s" in symbols_50
    assert "Step_Index" in symbols_50
    assert "EURUSD" in symbols_50

    # Ensure blowouts are excluded
    assert "Vol_75" not in symbols_50
    assert "Vol_250_1s" not in symbols_50
    assert "XAUUSD" not in symbols_50
