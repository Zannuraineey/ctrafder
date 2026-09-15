"""
Fast Scalping Data Models.
Domain models for live tick metrics, Depth of Market (DOM) order book, and composite Scalp Score.
(project.md Scalping V2 Architecture)
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from app.broker.models import TradeSide


class ScalpTier(str, Enum):
    NO_TRADE = "NO_TRADE"          # 0-49
    WEAK = "WEAK"                  # 50-64
    WATCH = "WATCH"                # 65-74
    GOOD = "GOOD"                  # 75-84
    HIGH_QUALITY = "HIGH_QUALITY"  # 85-100


@dataclass
class DOMQuote:
    """Depth of Market / Level II liquidity representation."""
    symbol: str
    bid_depth: float           # Aggregated bid liquidity in top levels
    ask_depth: float           # Aggregated ask liquidity in top levels
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def imbalance_ratio(self) -> float:
        """
        Order Book Imbalance: (Bid - Ask) / (Bid + Ask).
        Range: -1.0 (pure sell wall) to +1.0 (pure buy wall).
        """
        total = self.bid_depth + self.ask_depth
        if total <= 0:
            return 0.0
        return (self.bid_depth - self.ask_depth) / total


@dataclass
class TickMetric:
    """Real-time micro tick telemetry."""
    symbol: str
    last_price: float
    spread_points: float
    spread_ratio: float        # Current spread / typical ATR (lower is better)
    velocity_pts_sec: float    # Price velocity (dp/dt in points per second)
    acceleration: float        # Change in velocity
    tick_count_rate: float     # Ticks per second
    relative_activity: float   # Current tick volume / rolling average tick volume
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ScalpScore:
    """
    Composite Scalp Score (0-100) combining 8 Tier-1 quantitative factors:
    Spread (10%), Tick Momentum (20%), Price Velocity (15%), Volume Activity (15%),
    DOM Imbalance (15%), EMA Structure 5/9/20 (10%), ADX/DI (10%), ATR Volatility (5%).
    """
    symbol: str
    total_score: float         # 0 to 100
    tier: ScalpTier
    direction: Optional[TradeSide]
    is_eligible: bool          # True if total_score >= 75 and direction identified

    # Component Scores (0 to 100 each before weighting)
    spread_score: float        # 10%
    tick_momentum_score: float # 20%
    velocity_score: float      # 15%
    activity_score: float      # 15%
    dom_imbalance_score: float # 15%
    ema_structure_score: float # 10%
    adx_di_score: float        # 10%
    atr_volatility_score: float# 5%

    # Raw metrics for telemetry & post-mortem
    raw_velocity: float
    raw_activity_ratio: float
    raw_dom_imbalance: float
    raw_spread_points: float
    ema_alignment: str         # "BULLISH", "BEARISH", "MIXED"
    summary: str
