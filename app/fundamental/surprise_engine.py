"""
Macroeconomic Surprise Deviation Engine.
Quantifies Forecast vs. Actual economic surprises and maps them into cross-asset biases.
"""

from typing import Dict, Optional, Tuple
from datetime import datetime
from loguru import logger

from app.fundamental.calendar import EconomicEvent, EventImpact
from app.broker.models import TradeSide


# Historical standard deviations of consensus forecast errors
MACRO_HISTORICAL_STDEV: Dict[str, float] = {
    "cpi": 0.20,       # 0.2% typical deviation
    "nfp": 45.0,       # 45K payrolls typical deviation
    "rate": 0.15,      # 15 bps surprise
    "pmi": 1.5,        # 1.5 index points
    "gdp": 0.40,       # 0.4% GDP deviation
    "retail": 0.35,
}


class FundamentalBias:
    """Quantitative fundamental directional bias for an asset."""

    def __init__(self, symbol: str, bias_score: float, catalyst: str, surprise_z: float):
        self.symbol = symbol
        self.bias_score = bias_score  # -1.0 (Heavy Bearish) to +1.0 (Heavy Bullish)
        self.catalyst = catalyst
        self.surprise_z = surprise_z
        self.timestamp = datetime.utcnow()

    @property
    def recommended_side(self) -> Optional[TradeSide]:
        if self.bias_score >= 0.40:
            return TradeSide.BUY
        elif self.bias_score <= -0.40:
            return TradeSide.SELL
        return None


class SurpriseEngine:
    """
    Computes macroeconomic surprise Z-Scores and determines cross-asset catalysts.
    """

    @staticmethod
    def calculate_surprise_z(event: EconomicEvent) -> Optional[float]:
        """
        Calculate standardized surprise deviation: (Actual - Forecast) / StdDev.
        """
        if event.actual is None or event.forecast is None:
            return None

        diff = event.actual - event.forecast
        title_lower = event.title.lower()

        # Match historical standard deviation
        stdev = 0.50
        for key, val in MACRO_HISTORICAL_STDEV.items():
            if key in title_lower:
                stdev = val
                break

        z_score = diff / max(stdev, 1e-4)
        return round(float(z_score), 2)

    @classmethod
    def evaluate_symbol_bias(
        cls, symbol: str, event: EconomicEvent
    ) -> Optional[FundamentalBias]:
        """
        Determine how an economic release catalyst impacts a specific instrument.
        """
        z_score = cls.calculate_surprise_z(event)
        if z_score is None or abs(z_score) < 0.50:
            return None

        sym_upper = symbol.upper()
        ev_curr = event.currency.upper()
        title = event.title.lower()

        bias_score = 0.0

        # USD High-Impact Catalysts (CPI, NFP, Rates)
        if ev_curr == "USD":
            # Higher inflation/jobs = Hawkish USD = Strong USD
            is_hawkish_usd = z_score > 0
            # Flip for events where higher means weaker economy (e.g. Unemployment Rate)
            if "unemployment" in title or "claims" in title:
                is_hawkish_usd = z_score < 0

            usd_strength = 1.0 if is_hawkish_usd else -1.0
            magnitude = min(1.0, abs(z_score) / 2.5)

            if "XAUUSD" in sym_upper:
                # Strong USD / Rising Yields is strongly Bearish for Gold
                bias_score = -usd_strength * magnitude
            elif "EURUSD" in sym_upper or "GBPUSD" in sym_upper:
                # Strong USD pushes EURUSD / GBPUSD down
                bias_score = -usd_strength * magnitude
            elif "USDJPY" in sym_upper or "USDCAD" in sym_upper:
                # Strong USD pushes USDJPY up
                bias_score = usd_strength * magnitude
            elif "US100" in sym_upper or "US30" in sym_upper:
                # Hawkish surprise (higher rates) weighs on tech equities
                bias_score = -usd_strength * magnitude * 0.80

        # EUR High-Impact Catalysts (ECB Rates, German CPI)
        elif ev_curr == "EUR":
            eur_strength = 1.0 if z_score > 0 else -1.0
            magnitude = min(1.0, abs(z_score) / 2.5)
            if "EURUSD" in sym_upper:
                bias_score = eur_strength * magnitude

        # Synthetic indices (Deriv Volatility/Crash/Boom) are unimpacted by external news
        elif "VOL" in sym_upper or "CRASH" in sym_upper or "BOOM" in sym_upper or "RANGE" in sym_upper:
            return None

        if abs(bias_score) > 0.05:
            return FundamentalBias(
                symbol=symbol,
                bias_score=round(bias_score, 2),
                catalyst=f"{event.title} (Z: {z_score:+0.1f})",
                surprise_z=z_score,
            )

        return None
