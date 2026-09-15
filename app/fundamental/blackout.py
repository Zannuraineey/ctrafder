"""
Fundamental News Blackout & Spread Protection Shield.
Protects the fund from spread blowouts, extreme slippage, and whipsaw traps during Tier-1 events.
"""

from typing import Optional, List, Tuple
from datetime import datetime, timedelta
from loguru import logger

from app.fundamental.calendar import EconomicCalendar, EconomicEvent, EventImpact


class NewsBlackoutShield:
    """
    Evaluates whether an instrument is under a news blackout window.
    """

    def __init__(
        self,
        calendar: Optional[EconomicCalendar] = None,
        pre_event_minutes: int = 15,
        post_event_minutes: int = 2,
    ):
        self.calendar = calendar or EconomicCalendar()
        self.pre_event_minutes = pre_event_minutes
        self.post_event_minutes = post_event_minutes

    def is_symbol_affected_by_currency(self, symbol: str, currency: str) -> bool:
        """Check if symbol base/quote or asset class is tied to the event currency."""
        sym = symbol.upper()
        curr = currency.upper()

        if curr in sym:
            return True
        # Gold, Silver, Platinum, Oil, and Crypto are heavily impacted by USD releases
        if curr == "USD" and any(k in sym for k in ["XAU", "XAG", "XPT", "OIL", "US100", "US30", "NAS100", "BTC"]):
            return True
        return False

    def check_blackout(self, symbol: str) -> Tuple[bool, Optional[str]]:
        """
        Determine if trading on symbol must be blocked due to an imminent or recent high-impact release.
        Returns (is_blackout, reason_string).
        """
        # Deriv Synthetics are cryptographically generated and exempt from news blackouts
        sym_lower = symbol.lower()
        if any(k in sym_lower for k in ["vol_", "volatility", "crash", "boom", "range"]):
            return False, None

        now = datetime.utcnow()

        for ev in self.calendar.events:
            if ev.impact != EventImpact.HIGH:
                continue

            if not self.is_symbol_affected_by_currency(symbol, ev.currency):
                continue

            # Check pre-event window
            pre_start = ev.timestamp - timedelta(minutes=self.pre_event_minutes)
            if pre_start <= now <= ev.timestamp:
                mins_left = max(0, int((ev.timestamp - now).total_seconds() / 60))
                reason = f"NEWS BLACKOUT: Tier-1 event '{ev.title}' in {mins_left}m. Pre-event spread protection active."
                return True, reason

            # Check post-event cooldown window
            post_end = ev.timestamp + timedelta(minutes=self.post_event_minutes)
            if ev.timestamp < now <= post_end:
                secs_left = max(0, int((post_end - now).total_seconds()))
                reason = f"NEWS BLACKOUT: Tier-1 event '{ev.title}' just released. Post-event spread cooling ({secs_left}s remaining)."
                return True, reason

        return False, None
