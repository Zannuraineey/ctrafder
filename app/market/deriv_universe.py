"""
Comprehensive Deriv & cTrader Asset Catalog (~50+ Instruments).
Covers Derived Synthetics (Volatilities, Crash/Boom, Step, Range Break, Jump, Dex),
Metals & Commodities (Gold, Silver, Platinum, Oil), Forex (Majors & Crosses), and Crypto.
Each instrument includes exact lot constraints, contract size, tick metrics, and minimum account tier.
"""

from typing import Dict, List, Optional
from enum import Enum
from pydantic import BaseModel

from app.broker.models import SymbolSpecification


class AccountTier(str, Enum):
    MICRO = "MICRO"                  # $10 - $100: Safe for micro-lot trading only
    SMALL = "SMALL"                  # $100 - $500: Moderate risk, standard synthetic micro lots
    MEDIUM = "MEDIUM"                # $500 - $2,500: High volatility & Gold eligible
    INSTITUTIONAL = "INSTITUTIONAL"  # $2,500+: Full universe including high-impact synthetics


class DerivInstrumentMetadata(BaseModel):
    spec: SymbolSpecification
    tier: AccountTier
    typical_atr_points: float
    typical_spread_ticks: float
    volatility_rating: str           # "LOW", "MEDIUM", "HIGH", "EXTREME"
    blowout_risk_notes: str


DERIV_UNIVERSE_CATALOG: Dict[str, DerivInstrumentMetadata] = {
    # ==========================================
    # 1. CONTINUOUS VOLATILITY INDICES (5 Symbols)
    # ==========================================
    "Vol_10": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="Vol_10", symbol_id=101, description="Volatility 10 Index",
            asset_class="SYNTHETIC", digits=3, lot_min=0.20, lot_max=100.0, lot_step=0.01,
            contract_size=1.0, tick_size=0.001, tick_value=0.001, margin_rate=0.01
        ),
        tier=AccountTier.MICRO,
        typical_atr_points=1.8, typical_spread_ticks=4.0, volatility_rating="LOW",
        blowout_risk_notes="Low constant volatility. Highly safe for small accounts."
    ),
    "Vol_25": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="Vol_25", symbol_id=102, description="Volatility 25 Index",
            asset_class="SYNTHETIC", digits=3, lot_min=0.20, lot_max=100.0, lot_step=0.01,
            contract_size=1.0, tick_size=0.001, tick_value=0.001, margin_rate=0.01
        ),
        tier=AccountTier.MICRO,
        typical_atr_points=3.5, typical_spread_ticks=5.0, volatility_rating="LOW",
        blowout_risk_notes="Consistent trends, predictable swings. Great for micro accounts."
    ),
    "Vol_50": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="Vol_50", symbol_id=103, description="Volatility 50 Index",
            asset_class="SYNTHETIC", digits=4, lot_min=0.04, lot_max=50.0, lot_step=0.01,
            contract_size=1.0, tick_size=0.0001, tick_value=0.0001, margin_rate=0.01
        ),
        tier=AccountTier.SMALL,
        typical_atr_points=12.0, typical_spread_ticks=8.0, volatility_rating="MEDIUM",
        blowout_risk_notes="Moderate volatility. Needs careful stop loss sizing on sub-$100 accounts."
    ),
    "Vol_75": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="Vol_75", symbol_id=104, description="Volatility 75 Index",
            asset_class="SYNTHETIC", digits=4, lot_min=0.001, lot_max=20.0, lot_step=0.001,
            contract_size=1.0, tick_size=0.0001, tick_value=0.0001, margin_rate=0.02
        ),
        tier=AccountTier.MEDIUM,
        typical_atr_points=850.0, typical_spread_ticks=15.0, volatility_rating="EXTREME",
        blowout_risk_notes="EXTREME BLOWOUT RISK. High pip value. Will wipe a $50 account on minor wick."
    ),
    "Vol_100": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="Vol_100", symbol_id=105, description="Volatility 100 Index",
            asset_class="SYNTHETIC", digits=2, lot_min=0.10, lot_max=50.0, lot_step=0.01,
            contract_size=1.0, tick_size=0.01, tick_value=0.01, margin_rate=0.02
        ),
        tier=AccountTier.MEDIUM,
        typical_atr_points=35.0, typical_spread_ticks=10.0, volatility_rating="HIGH",
        blowout_risk_notes="Rapid price momentum. Minimum risk requires at least $250+ balance."
    ),

    # ==========================================
    # 2. VOLATILITY (1s) FAST INDICES (10 Symbols)
    # ==========================================
    "Vol_10_1s": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="Vol_10_1s", symbol_id=110, description="Volatility 10 (1s) Index",
            asset_class="SYNTHETIC", digits=4, lot_min=0.20, lot_max=100.0, lot_step=0.01,
            contract_size=1.0, tick_size=0.0001, tick_value=0.0001, margin_rate=0.01
        ),
        tier=AccountTier.MICRO,
        typical_atr_points=1.2, typical_spread_ticks=3.0, volatility_rating="LOW",
        blowout_risk_notes="Best starting synthetic for $10–$50 micro accounts. Smooth moves."
    ),
    "Vol_15_1s": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="Vol_15_1s", symbol_id=111, description="Volatility 15 (1s) Index",
            asset_class="SYNTHETIC", digits=4, lot_min=0.10, lot_max=100.0, lot_step=0.01,
            contract_size=1.0, tick_size=0.0001, tick_value=0.0001, margin_rate=0.01
        ),
        tier=AccountTier.MICRO,
        typical_atr_points=2.1, typical_spread_ticks=4.0, volatility_rating="LOW",
        blowout_risk_notes="Excellent low-risk intraday vehicle. Minimum stop risk is <$0.50."
    ),
    "Vol_25_1s": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="Vol_25_1s", symbol_id=112, description="Volatility 25 (1s) Index",
            asset_class="SYNTHETIC", digits=4, lot_min=0.10, lot_max=100.0, lot_step=0.01,
            contract_size=1.0, tick_size=0.0001, tick_value=0.0001, margin_rate=0.01
        ),
        tier=AccountTier.MICRO,
        typical_atr_points=3.8, typical_spread_ticks=5.0, volatility_rating="LOW",
        blowout_risk_notes="Stable micro scalping asset. High responsiveness with minimal slippage."
    ),
    "Vol_30_1s": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="Vol_30_1s", symbol_id=113, description="Volatility 30 (1s) Index",
            asset_class="SYNTHETIC", digits=4, lot_min=0.10, lot_max=100.0, lot_step=0.01,
            contract_size=1.0, tick_size=0.0001, tick_value=0.0001, margin_rate=0.01
        ),
        tier=AccountTier.SMALL,
        typical_atr_points=5.0, typical_spread_ticks=6.0, volatility_rating="MEDIUM",
        blowout_risk_notes="Moderate speed. Manageable for $100 accounts."
    ),
    "Vol_50_1s": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="Vol_50_1s", symbol_id=114, description="Volatility 50 (1s) Index",
            asset_class="SYNTHETIC", digits=4, lot_min=0.05, lot_max=50.0, lot_step=0.01,
            contract_size=1.0, tick_size=0.0001, tick_value=0.0001, margin_rate=0.01
        ),
        tier=AccountTier.SMALL,
        typical_atr_points=14.0, typical_spread_ticks=8.0, volatility_rating="MEDIUM",
        blowout_risk_notes="Fast swings every second. Requires disciplined dynamic SL."
    ),
    "Vol_75_1s": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="Vol_75_1s", symbol_id=115, description="Volatility 75 (1s) Index",
            asset_class="SYNTHETIC", digits=4, lot_min=0.005, lot_max=20.0, lot_step=0.001,
            contract_size=1.0, tick_size=0.0001, tick_value=0.0001, margin_rate=0.02
        ),
        tier=AccountTier.MEDIUM,
        typical_atr_points=420.0, typical_spread_ticks=12.0, volatility_rating="HIGH",
        blowout_risk_notes="High spike velocity. Do not trade with accounts under $500."
    ),
    "Vol_90_1s": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="Vol_90_1s", symbol_id=116, description="Volatility 90 (1s) Index",
            asset_class="SYNTHETIC", digits=4, lot_min=0.10, lot_max=50.0, lot_step=0.01,
            contract_size=1.0, tick_size=0.0001, tick_value=0.0001, margin_rate=0.02
        ),
        tier=AccountTier.MEDIUM,
        typical_atr_points=28.0, typical_spread_ticks=10.0, volatility_rating="HIGH",
        blowout_risk_notes="Strong impulse legs. Suitable for momentum scalping with adequate margin."
    ),
    "Vol_100_1s": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="Vol_100_1s", symbol_id=117, description="Volatility 100 (1s) Index",
            asset_class="SYNTHETIC", digits=2, lot_min=0.10, lot_max=50.0, lot_step=0.01,
            contract_size=1.0, tick_size=0.01, tick_value=0.01, margin_rate=0.02
        ),
        tier=AccountTier.MEDIUM,
        typical_atr_points=45.0, typical_spread_ticks=12.0, volatility_rating="HIGH",
        blowout_risk_notes="Very fast tick rate. High reward but dangerous for under-capitalized accounts."
    ),
    "Vol_150_1s": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="Vol_150_1s", symbol_id=118, description="Volatility 150 (1s) Index",
            asset_class="SYNTHETIC", digits=4, lot_min=0.05, lot_max=30.0, lot_step=0.01,
            contract_size=1.0, tick_size=0.0001, tick_value=0.0001, margin_rate=0.03
        ),
        tier=AccountTier.INSTITUTIONAL,
        typical_atr_points=120.0, typical_spread_ticks=16.0, volatility_rating="EXTREME",
        blowout_risk_notes="Severe volatility. Reserved for $2500+ institutional risk budgets."
    ),
    "Vol_250_1s": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="Vol_250_1s", symbol_id=119, description="Volatility 250 (1s) Index",
            asset_class="SYNTHETIC", digits=4, lot_min=0.05, lot_max=20.0, lot_step=0.01,
            contract_size=1.0, tick_size=0.0001, tick_value=0.0001, margin_rate=0.04
        ),
        tier=AccountTier.INSTITUTIONAL,
        typical_atr_points=260.0, typical_spread_ticks=25.0, volatility_rating="EXTREME",
        blowout_risk_notes="Highest volatility synthetic. Instant liquidation risk if mis-sized."
    ),

    # ==========================================
    # 3. CRASH & BOOM INDICES (10 Symbols)
    # ==========================================
    "Crash_300": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="Crash_300", symbol_id=120, description="Crash 300 Index",
            asset_class="SYNTHETIC", digits=4, lot_min=0.20, lot_max=50.0, lot_step=0.01,
            contract_size=1.0, tick_size=0.0001, tick_value=0.0001, margin_rate=0.02
        ),
        tier=AccountTier.SMALL,
        typical_atr_points=18.0, typical_spread_ticks=6.0, volatility_rating="HIGH",
        blowout_risk_notes="Crashes occur frequently (~every 300 ticks). Long trades must have tight SL!"
    ),
    "Crash_500": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="Crash_500", symbol_id=121, description="Crash 500 Index",
            asset_class="SYNTHETIC", digits=4, lot_min=0.20, lot_max=50.0, lot_step=0.01,
            contract_size=1.0, tick_size=0.0001, tick_value=0.0001, margin_rate=0.02
        ),
        tier=AccountTier.SMALL,
        typical_atr_points=24.0, typical_spread_ticks=7.0, volatility_rating="HIGH",
        blowout_risk_notes="Severe sudden downward drops. Never hold Long without immediate stop protection."
    ),
    "Crash_600": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="Crash_600", symbol_id=122, description="Crash 600 Index",
            asset_class="SYNTHETIC", digits=4, lot_min=0.20, lot_max=50.0, lot_step=0.01,
            contract_size=1.0, tick_size=0.0001, tick_value=0.0001, margin_rate=0.02
        ),
        tier=AccountTier.MEDIUM,
        typical_atr_points=32.0, typical_spread_ticks=8.0, volatility_rating="HIGH",
        blowout_risk_notes="Large drop magnitude. Requires $500+ equity."
    ),
    "Crash_900": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="Crash_900", symbol_id=123, description="Crash 900 Index",
            asset_class="SYNTHETIC", digits=4, lot_min=0.20, lot_max=50.0, lot_step=0.01,
            contract_size=1.0, tick_size=0.0001, tick_value=0.0001, margin_rate=0.02
        ),
        tier=AccountTier.MEDIUM,
        typical_atr_points=45.0, typical_spread_ticks=9.0, volatility_rating="HIGH",
        blowout_risk_notes="Infrequent but catastrophic drops. Shorting pullbacks is primary strategy."
    ),
    "Crash_1000": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="Crash_1000", symbol_id=124, description="Crash 1000 Index",
            asset_class="SYNTHETIC", digits=4, lot_min=0.20, lot_max=50.0, lot_step=0.01,
            contract_size=1.0, tick_size=0.0001, tick_value=0.0001, margin_rate=0.02
        ),
        tier=AccountTier.MEDIUM,
        typical_atr_points=60.0, typical_spread_ticks=10.0, volatility_rating="HIGH",
        blowout_risk_notes="Classic Deriv crash. Spikes can drop 50-100 points in 1 tick."
    ),
    "Boom_300": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="Boom_300", symbol_id=125, description="Boom 300 Index",
            asset_class="SYNTHETIC", digits=4, lot_min=0.20, lot_max=50.0, lot_step=0.01,
            contract_size=1.0, tick_size=0.0001, tick_value=0.0001, margin_rate=0.02
        ),
        tier=AccountTier.SMALL,
        typical_atr_points=18.0, typical_spread_ticks=6.0, volatility_rating="HIGH",
        blowout_risk_notes="Upward spikes occur ~every 300 ticks. Shorting without hard SL is fatal."
    ),
    "Boom_500": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="Boom_500", symbol_id=126, description="Boom 500 Index",
            asset_class="SYNTHETIC", digits=4, lot_min=0.20, lot_max=50.0, lot_step=0.01,
            contract_size=1.0, tick_size=0.0001, tick_value=0.0001, margin_rate=0.02
        ),
        tier=AccountTier.SMALL,
        typical_atr_points=25.0, typical_spread_ticks=7.0, volatility_rating="HIGH",
        blowout_risk_notes="Sudden explosive vertical spikes. Great for buy-dip scalping."
    ),
    "Boom_600": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="Boom_600", symbol_id=127, description="Boom 600 Index",
            asset_class="SYNTHETIC", digits=4, lot_min=0.20, lot_max=50.0, lot_step=0.01,
            contract_size=1.0, tick_size=0.0001, tick_value=0.0001, margin_rate=0.02
        ),
        tier=AccountTier.MEDIUM,
        typical_atr_points=34.0, typical_spread_ticks=8.0, volatility_rating="HIGH",
        blowout_risk_notes="Large upward spike amplitude. Requires moderate equity cushion."
    ),
    "Boom_900": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="Boom_900", symbol_id=128, description="Boom 900 Index",
            asset_class="SYNTHETIC", digits=4, lot_min=0.20, lot_max=50.0, lot_step=0.01,
            contract_size=1.0, tick_size=0.0001, tick_value=0.0001, margin_rate=0.02
        ),
        tier=AccountTier.MEDIUM,
        typical_atr_points=48.0, typical_spread_ticks=9.0, volatility_rating="HIGH",
        blowout_risk_notes="Smooth downward drift followed by massive upward spike."
    ),
    "Boom_1000": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="Boom_1000", symbol_id=129, description="Boom 1000 Index",
            asset_class="SYNTHETIC", digits=4, lot_min=0.20, lot_max=50.0, lot_step=0.01,
            contract_size=1.0, tick_size=0.0001, tick_value=0.0001, margin_rate=0.02
        ),
        tier=AccountTier.MEDIUM,
        typical_atr_points=65.0, typical_spread_ticks=10.0, volatility_rating="HIGH",
        blowout_risk_notes="Massive vertical spikes. Unhedged shorting will blow an account in seconds."
    ),

    # ==========================================
    # 4. STEP & RANGE BREAK INDICES (5 Symbols)
    # ==========================================
    "Step_Index": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="Step_Index", symbol_id=130, description="Step Index",
            asset_class="SYNTHETIC", digits=1, lot_min=0.10, lot_max=50.0, lot_step=0.01,
            contract_size=1.0, tick_size=0.1, tick_value=0.1, margin_rate=0.01
        ),
        tier=AccountTier.MICRO,
        typical_atr_points=4.0, typical_spread_ticks=2.0, volatility_rating="LOW",
        blowout_risk_notes="Equal step probabilities (0.1 points). Highly recommended for small accounts!"
    ),
    "Step_200": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="Step_200", symbol_id=131, description="Step 200 Index",
            asset_class="SYNTHETIC", digits=1, lot_min=0.10, lot_max=50.0, lot_step=0.01,
            contract_size=1.0, tick_size=0.1, tick_value=0.1, margin_rate=0.01
        ),
        tier=AccountTier.MICRO,
        typical_atr_points=6.0, typical_spread_ticks=3.0, volatility_rating="LOW",
        blowout_risk_notes="Predictable quantization steps. Minimal slippage risk."
    ),
    "Step_500": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="Step_500", symbol_id=132, description="Step 500 Index",
            asset_class="SYNTHETIC", digits=1, lot_min=0.10, lot_max=50.0, lot_step=0.01,
            contract_size=1.0, tick_size=0.1, tick_value=0.1, margin_rate=0.01
        ),
        tier=AccountTier.SMALL,
        typical_atr_points=10.0, typical_spread_ticks=4.0, volatility_rating="MEDIUM",
        blowout_risk_notes="Larger step runs. Very disciplined trend pullback candidate."
    ),
    "Range_Break_100": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="Range_Break_100", symbol_id=133, description="Range Break 100 Index",
            asset_class="SYNTHETIC", digits=2, lot_min=0.05, lot_max=30.0, lot_step=0.01,
            contract_size=1.0, tick_size=0.01, tick_value=0.01, margin_rate=0.02
        ),
        tier=AccountTier.SMALL,
        typical_atr_points=8.0, typical_spread_ticks=5.0, volatility_rating="MEDIUM",
        blowout_risk_notes="Oscillates inside borders then breaks out ~every 100 attempts. Manage fakeouts."
    ),
    "Range_Break_200": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="Range_Break_200", symbol_id=134, description="Range Break 200 Index",
            asset_class="SYNTHETIC", digits=2, lot_min=0.05, lot_max=30.0, lot_step=0.01,
            contract_size=1.0, tick_size=0.01, tick_value=0.01, margin_rate=0.02
        ),
        tier=AccountTier.SMALL,
        typical_atr_points=14.0, typical_spread_ticks=6.0, volatility_rating="MEDIUM",
        blowout_risk_notes="Longer consolidation periods before expansion break. High win-rate setup."
    ),

    # ==========================================
    # 5. JUMP & DEX INDICES (8 Symbols)
    # ==========================================
    "Jump_10": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="Jump_10", symbol_id=140, description="Jump 10 Index",
            asset_class="SYNTHETIC", digits=2, lot_min=0.10, lot_max=50.0, lot_step=0.01,
            contract_size=1.0, tick_size=0.01, tick_value=0.01, margin_rate=0.02
        ),
        tier=AccountTier.SMALL,
        typical_atr_points=12.0, typical_spread_ticks=5.0, volatility_rating="MEDIUM",
        blowout_risk_notes="Periodic price jumps. Standard synthetic risk."
    ),
    "Jump_25": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="Jump_25", symbol_id=141, description="Jump 25 Index",
            asset_class="SYNTHETIC", digits=2, lot_min=0.10, lot_max=50.0, lot_step=0.01,
            contract_size=1.0, tick_size=0.01, tick_value=0.01, margin_rate=0.02
        ),
        tier=AccountTier.SMALL,
        typical_atr_points=25.0, typical_spread_ticks=6.0, volatility_rating="MEDIUM",
        blowout_risk_notes="Moderate jump magnitude. Trade with clear structure SL."
    ),
    "Jump_50": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="Jump_50", symbol_id=142, description="Jump 50 Index",
            asset_class="SYNTHETIC", digits=2, lot_min=0.05, lot_max=30.0, lot_step=0.01,
            contract_size=1.0, tick_size=0.01, tick_value=0.01, margin_rate=0.02
        ),
        tier=AccountTier.MEDIUM,
        typical_atr_points=50.0, typical_spread_ticks=8.0, volatility_rating="HIGH",
        blowout_risk_notes="Aggressive jumps. Risk threshold must be $500+."
    ),
    "Jump_75": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="Jump_75", symbol_id=143, description="Jump 75 Index",
            asset_class="SYNTHETIC", digits=2, lot_min=0.05, lot_max=20.0, lot_step=0.01,
            contract_size=1.0, tick_size=0.01, tick_value=0.01, margin_rate=0.03
        ),
        tier=AccountTier.MEDIUM,
        typical_atr_points=80.0, typical_spread_ticks=10.0, volatility_rating="HIGH",
        blowout_risk_notes="Severe jumps. Not suitable for micro accounts."
    ),
    "Jump_100": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="Jump_100", symbol_id=144, description="Jump 100 Index",
            asset_class="SYNTHETIC", digits=2, lot_min=0.05, lot_max=20.0, lot_step=0.01,
            contract_size=1.0, tick_size=0.01, tick_value=0.01, margin_rate=0.03
        ),
        tier=AccountTier.INSTITUTIONAL,
        typical_atr_points=120.0, typical_spread_ticks=15.0, volatility_rating="EXTREME",
        blowout_risk_notes="Extreme jump volatility. Can gap through stops."
    ),
    "Dex_600": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="Dex_600", symbol_id=145, description="Dex 600 Index",
            asset_class="SYNTHETIC", digits=3, lot_min=0.20, lot_max=50.0, lot_step=0.01,
            contract_size=1.0, tick_size=0.001, tick_value=0.001, margin_rate=0.02
        ),
        tier=AccountTier.SMALL,
        typical_atr_points=15.0, typical_spread_ticks=5.0, volatility_rating="MEDIUM",
        blowout_risk_notes="Discreet event synthetic index."
    ),
    "Dex_900": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="Dex_900", symbol_id=146, description="Dex 900 Index",
            asset_class="SYNTHETIC", digits=3, lot_min=0.20, lot_max=50.0, lot_step=0.01,
            contract_size=1.0, tick_size=0.001, tick_value=0.001, margin_rate=0.02
        ),
        tier=AccountTier.SMALL,
        typical_atr_points=22.0, typical_spread_ticks=6.0, volatility_rating="MEDIUM",
        blowout_risk_notes="Reliable mean-reversion characteristics."
    ),
    "Dex_1500": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="Dex_1500", symbol_id=147, description="Dex 1500 Index",
            asset_class="SYNTHETIC", digits=3, lot_min=0.20, lot_max=50.0, lot_step=0.01,
            contract_size=1.0, tick_size=0.001, tick_value=0.001, margin_rate=0.02
        ),
        tier=AccountTier.MEDIUM,
        typical_atr_points=35.0, typical_spread_ticks=8.0, volatility_rating="HIGH",
        blowout_risk_notes="Extended trending waves."
    ),

    # ==========================================
    # 6. METALS & COMMODITIES (6 Symbols)
    # ==========================================
    "XAUUSD": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="XAUUSD", symbol_id=1, description="Gold vs US Dollar",
            asset_class="METALS", digits=2, lot_min=0.01, lot_max=20.0, lot_step=0.01,
            contract_size=100.0, tick_size=0.01, tick_value=1.0, margin_rate=0.01
        ),
        tier=AccountTier.MEDIUM,
        typical_atr_points=25.0, typical_spread_ticks=25.0, volatility_rating="HIGH",
        blowout_risk_notes="HIGH BLOWOUT RISK on small accounts! 0.01 lot with 100 pt SL = $10 risk (20% of $50)."
    ),
    "XAGUSD": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="XAGUSD", symbol_id=2, description="Silver vs US Dollar",
            asset_class="METALS", digits=3, lot_min=0.01, lot_max=10.0, lot_step=0.01,
            contract_size=5000.0, tick_size=0.001, tick_value=5.0, margin_rate=0.02
        ),
        tier=AccountTier.SMALL,
        typical_atr_points=0.75, typical_spread_ticks=30.0, volatility_rating="MEDIUM",
        blowout_risk_notes="Large contract size ($5/pt on 1 lot). Requires strict lot calculation."
    ),
    "XPTUSD": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="XPTUSD", symbol_id=3, description="Platinum vs US Dollar",
            asset_class="METALS", digits=2, lot_min=0.01, lot_max=10.0, lot_step=0.01,
            contract_size=100.0, tick_size=0.01, tick_value=1.0, margin_rate=0.02
        ),
        tier=AccountTier.MEDIUM,
        typical_atr_points=18.0, typical_spread_ticks=35.0, volatility_rating="HIGH",
        blowout_risk_notes="Industrial precious metal. Wide spreads during Asian session."
    ),
    "XPDUSD": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="XPDUSD", symbol_id=4, description="Palladium vs US Dollar",
            asset_class="METALS", digits=2, lot_min=0.01, lot_max=10.0, lot_step=0.01,
            contract_size=100.0, tick_size=0.01, tick_value=1.0, margin_rate=0.03
        ),
        tier=AccountTier.INSTITUTIONAL,
        typical_atr_points=35.0, typical_spread_ticks=50.0, volatility_rating="EXTREME",
        blowout_risk_notes="Low liquidity, wide spread. Minimum $2,500 account required."
    ),
    "US_OIL": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="US_OIL", symbol_id=5, description="WTI Crude Oil",
            asset_class="COMMODITIES", digits=2, lot_min=0.01, lot_max=50.0, lot_step=0.01,
            contract_size=100.0, tick_size=0.01, tick_value=1.0, margin_rate=0.02
        ),
        tier=AccountTier.SMALL,
        typical_atr_points=1.80, typical_spread_ticks=15.0, volatility_rating="MEDIUM",
        blowout_risk_notes="Sensitive to OPEC & EIA inventory releases. Avoid trading during EIA."
    ),
    "UK_OIL": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="UK_OIL", symbol_id=6, description="Brent Crude Oil",
            asset_class="COMMODITIES", digits=2, lot_min=0.01, lot_max=50.0, lot_step=0.01,
            contract_size=100.0, tick_size=0.01, tick_value=1.0, margin_rate=0.02
        ),
        tier=AccountTier.SMALL,
        typical_atr_points=1.90, typical_spread_ticks=16.0, volatility_rating="MEDIUM",
        blowout_risk_notes="Global oil benchmark. Good liquidity during European/US overlap."
    ),

    # ==========================================
    # 7. FOREX MAJORS & CROSSES (11 Symbols)
    # ==========================================
    "EURUSD": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="EURUSD", symbol_id=10, description="Euro vs US Dollar",
            asset_class="FOREX", digits=5, lot_min=0.01, lot_max=50.0, lot_step=0.01,
            contract_size=100000.0, tick_size=0.00001, tick_value=1.0, margin_rate=0.01
        ),
        tier=AccountTier.MICRO,
        typical_atr_points=0.0007, typical_spread_ticks=12.0, volatility_rating="LOW",
        blowout_risk_notes="MOST LIQUID ASSET ON EARTH. Perfect for $10-$50 accounts at 0.01 lots!"
    ),
    "GBPUSD": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="GBPUSD", symbol_id=11, description="British Pound vs US Dollar",
            asset_class="FOREX", digits=5, lot_min=0.01, lot_max=50.0, lot_step=0.01,
            contract_size=100000.0, tick_size=0.00001, tick_value=1.0, margin_rate=0.01
        ),
        tier=AccountTier.MICRO,
        typical_atr_points=0.0009, typical_spread_ticks=15.0, volatility_rating="LOW",
        blowout_risk_notes="Higher pip movement than EURUSD, but 0.01 lot keeps risk strictly ~$1.00."
    ),
    "USDJPY": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="USDJPY", symbol_id=12, description="US Dollar vs Japanese Yen",
            asset_class="FOREX", digits=3, lot_min=0.01, lot_max=50.0, lot_step=0.01,
            contract_size=100000.0, tick_size=0.001, tick_value=0.67, margin_rate=0.01
        ),
        tier=AccountTier.MICRO,
        typical_atr_points=0.10, typical_spread_ticks=14.0, volatility_rating="LOW",
        blowout_risk_notes="Clean institutional trend dynamics. Very safe for small accounts."
    ),
    "AUDUSD": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="AUDUSD", symbol_id=13, description="Australian Dollar vs US Dollar",
            asset_class="FOREX", digits=5, lot_min=0.01, lot_max=50.0, lot_step=0.01,
            contract_size=100000.0, tick_size=0.00001, tick_value=1.0, margin_rate=0.01
        ),
        tier=AccountTier.MICRO,
        typical_atr_points=0.0006, typical_spread_ticks=14.0, volatility_rating="LOW",
        blowout_risk_notes="Commodity currency. Safe micro account vehicle."
    ),
    "USDCAD": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="USDCAD", symbol_id=14, description="US Dollar vs Canadian Dollar",
            asset_class="FOREX", digits=5, lot_min=0.01, lot_max=50.0, lot_step=0.01,
            contract_size=100000.0, tick_size=0.00001, tick_value=0.74, margin_rate=0.01
        ),
        tier=AccountTier.MICRO,
        typical_atr_points=0.0007, typical_spread_ticks=15.0, volatility_rating="LOW",
        blowout_risk_notes="Oil correlated. Excellent for swing and scalping setups."
    ),
    "USDCHF": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="USDCHF", symbol_id=15, description="US Dollar vs Swiss Franc",
            asset_class="FOREX", digits=5, lot_min=0.01, lot_max=50.0, lot_step=0.01,
            contract_size=100000.0, tick_size=0.00001, tick_value=1.12, margin_rate=0.01
        ),
        tier=AccountTier.MICRO,
        typical_atr_points=0.0006, typical_spread_ticks=16.0, volatility_rating="LOW",
        blowout_risk_notes="Safe-haven asset. Low whipsaw probability."
    ),
    "NZDUSD": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="NZDUSD", symbol_id=16, description="New Zealand Dollar vs US Dollar",
            asset_class="FOREX", digits=5, lot_min=0.01, lot_max=50.0, lot_step=0.01,
            contract_size=100000.0, tick_size=0.00001, tick_value=1.0, margin_rate=0.01
        ),
        tier=AccountTier.MICRO,
        typical_atr_points=0.0006, typical_spread_ticks=18.0, volatility_rating="LOW",
        blowout_risk_notes="Small pip value, highly manageable risk."
    ),
    "EURGBP": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="EURGBP", symbol_id=17, description="Euro vs British Pound",
            asset_class="FOREX", digits=5, lot_min=0.01, lot_max=50.0, lot_step=0.01,
            contract_size=100000.0, tick_size=0.00001, tick_value=1.28, margin_rate=0.01
        ),
        tier=AccountTier.MICRO,
        typical_atr_points=0.0005, typical_spread_ticks=18.0, volatility_rating="LOW",
        blowout_risk_notes="Slow-moving range instrument. Very safe for conservative trading."
    ),
    "EURJPY": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="EURJPY", symbol_id=18, description="Euro vs Japanese Yen",
            asset_class="FOREX", digits=3, lot_min=0.01, lot_max=50.0, lot_step=0.01,
            contract_size=100000.0, tick_size=0.001, tick_value=0.67, margin_rate=0.01
        ),
        tier=AccountTier.SMALL,
        typical_atr_points=1.10, typical_spread_ticks=18.0, volatility_rating="MEDIUM",
        blowout_risk_notes="Trending cross. Higher momentum than majors."
    ),
    "GBPJPY": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="GBPJPY", symbol_id=19, description="British Pound vs Japanese Yen",
            asset_class="FOREX", digits=3, lot_min=0.01, lot_max=50.0, lot_step=0.01,
            contract_size=100000.0, tick_size=0.001, tick_value=0.67, margin_rate=0.01
        ),
        tier=AccountTier.SMALL,
        typical_atr_points=1.60, typical_spread_ticks=22.0, volatility_rating="HIGH",
        blowout_risk_notes="'The Dragon'. Fast, large moves. Recommended for $250+ accounts."
    ),
    "AUDJPY": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="AUDJPY", symbol_id=20, description="Australian Dollar vs Japanese Yen",
            asset_class="FOREX", digits=3, lot_min=0.01, lot_max=50.0, lot_step=0.01,
            contract_size=100000.0, tick_size=0.001, tick_value=0.67, margin_rate=0.01
        ),
        tier=AccountTier.MICRO,
        typical_atr_points=0.85, typical_spread_ticks=18.0, volatility_rating="LOW",
        blowout_risk_notes="Risk-sentiment indicator. Good stability for small accounts."
    ),

    # ==========================================
    # 8. CRYPTOCURRENCIES (2 Symbols)
    # ==========================================
    "BTCUSD": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="BTCUSD", symbol_id=30, description="Bitcoin vs US Dollar",
            asset_class="CRYPTO", digits=2, lot_min=0.01, lot_max=10.0, lot_step=0.01,
            contract_size=1.0, tick_size=0.01, tick_value=0.01, margin_rate=0.05
        ),
        tier=AccountTier.MEDIUM,
        typical_atr_points=1200.0, typical_spread_ticks=80.0, volatility_rating="HIGH",
        blowout_risk_notes="High dollar volatility. 0.01 lot has $12 risk on 1200 pt stop."
    ),
    "ETHUSD": DerivInstrumentMetadata(
        spec=SymbolSpecification(
            symbol="ETHUSD", symbol_id=31, description="Ethereum vs US Dollar",
            asset_class="CRYPTO", digits=2, lot_min=0.01, lot_max=20.0, lot_step=0.01,
            contract_size=1.0, tick_size=0.01, tick_value=0.01, margin_rate=0.05
        ),
        tier=AccountTier.SMALL,
        typical_atr_points=85.0, typical_spread_ticks=40.0, volatility_rating="HIGH",
        blowout_risk_notes="Active crypto trading instrument. Better suited for sub-$500 accounts than BTC."
    ),
}


class DerivUniverseRegistry:
    """
    Registry providing quick access, search, and filtering across the full Deriv cTrader universe.
    """

    @staticmethod
    def get_all_symbols() -> List[SymbolSpecification]:
        return [meta.spec for meta in DERIV_UNIVERSE_CATALOG.values()]

    @staticmethod
    def get_metadata(symbol: str) -> Optional[DerivInstrumentMetadata]:
        return DERIV_UNIVERSE_CATALOG.get(symbol)

    @staticmethod
    def get_symbols_by_tier(max_tier: AccountTier) -> List[SymbolSpecification]:
        tier_hierarchy = {
            AccountTier.MICRO: 1,
            AccountTier.SMALL: 2,
            AccountTier.MEDIUM: 3,
            AccountTier.INSTITUTIONAL: 4,
        }
        max_level = tier_hierarchy[max_tier]
        return [
            meta.spec
            for meta in DERIV_UNIVERSE_CATALOG.values()
            if tier_hierarchy[meta.tier] <= max_level
        ]

    @staticmethod
    def get_symbols_by_asset_class(asset_class: str) -> List[SymbolSpecification]:
        return [
            meta.spec
            for meta in DERIV_UNIVERSE_CATALOG.values()
            if meta.spec.asset_class.upper() == asset_class.upper()
        ]
