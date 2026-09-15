"""
Economic Calendar & Fundamental Event Ingestion Engine.
Tracks global macroeconomic releases (CPI, NFP, FOMC, GDP, PMI, Central Bank Decisions).
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
from pydantic import BaseModel, Field


class EventImpact(str, Enum):
    HIGH = "HIGH"      # Tier-1: FOMC, NFP, CPI, Central Bank Rate Decisions
    MEDIUM = "MEDIUM"  # Tier-2: Retail Sales, PMI, PPI, GDP revisions
    LOW = "LOW"        # Tier-3: Secondary indicators, regional surveys


class EconomicEvent(BaseModel):
    id: str
    title: str
    currency: str          # e.g., USD, EUR, GBP, JPY
    impact: EventImpact
    timestamp: datetime
    forecast: Optional[float] = None
    previous: Optional[float] = None
    actual: Optional[float] = None
    unit: str = "%"        # "%", "K", "B", "Index"
    source: str = "EconomicCalendar"

    @property
    def is_released(self) -> bool:
        return self.actual is not None


class EconomicCalendar:
    """
    Maintains upcoming and historical economic calendar events.
    Supports live feed integration and built-in institutional mock calendars.
    """

    def __init__(self):
        self.events: List[EconomicEvent] = []
        self._init_benchmark_events()

    def _init_benchmark_events(self) -> None:
        """Populate realistic macro release schedule anchored relative to current time."""
        now = datetime.utcnow()
        self.events = [
            EconomicEvent(
                id="cpi_usd_001",
                title="US Core CPI (YoY)",
                currency="USD",
                impact=EventImpact.HIGH,
                timestamp=now + timedelta(minutes=24, seconds=30),
                forecast=3.2,
                previous=3.4,
                actual=None,
                unit="%",
            ),
            EconomicEvent(
                id="pmi_usd_001",
                title="US ISM Manufacturing PMI",
                currency="USD",
                impact=EventImpact.MEDIUM,
                timestamp=now + timedelta(minutes=55),
                forecast=49.5,
                previous=48.8,
                actual=None,
                unit="Index",
            ),
            EconomicEvent(
                id="nfp_usd_002",
                title="US Non-Farm Payrolls",
                currency="USD",
                impact=EventImpact.HIGH,
                timestamp=now + timedelta(hours=2, minutes=15),
                forecast=180.0,
                previous=175.0,
                actual=None,
                unit="K",
            ),
            EconomicEvent(
                id="fomc_usd_003",
                title="Federal Reserve Interest Rate Decision",
                currency="USD",
                impact=EventImpact.HIGH,
                timestamp=now + timedelta(hours=5),
                forecast=5.25,
                previous=5.25,
                actual=None,
                unit="%",
            ),
            EconomicEvent(
                id="ecb_eur_001",
                title="ECB Main Refinancing Rate",
                currency="EUR",
                impact=EventImpact.HIGH,
                timestamp=now + timedelta(hours=8),
                forecast=3.75,
                previous=4.00,
                actual=None,
                unit="%",
            ),
            # Recently released event for post-release analysis
            EconomicEvent(
                id="retail_usd_004",
                title="US Core Retail Sales (MoM)",
                currency="USD",
                impact=EventImpact.MEDIUM,
                timestamp=now - timedelta(minutes=25),
                forecast=0.3,
                previous=0.1,
                actual=0.5,
                unit="%",
            ),
        ]

    def add_event(self, event: EconomicEvent) -> None:
        self.events.append(event)

    def get_upcoming_events(
        self,
        window_minutes: int = 60,
        min_impact: EventImpact = EventImpact.MEDIUM,
        currency: Optional[str] = None,
    ) -> List[EconomicEvent]:
        """
        Return upcoming releases within window_minutes from current time.
        """
        now = datetime.utcnow()
        limit_time = now + timedelta(minutes=window_minutes)

        impact_order = {EventImpact.LOW: 1, EventImpact.MEDIUM: 2, EventImpact.HIGH: 3}
        min_level = impact_order[min_impact]

        results = []
        for ev in self.events:
            if currency and ev.currency != currency:
                continue
            if impact_order[ev.impact] < min_level:
                continue
            if now <= ev.timestamp <= limit_time:
                results.append(ev)

        results.sort(key=lambda x: x.timestamp)
        return results

    def get_recent_releases(
        self, window_minutes: int = 60, currency: Optional[str] = None
    ) -> List[EconomicEvent]:
        """
        Return released events within the last window_minutes.
        """
        now = datetime.utcnow()
        start_time = now - timedelta(minutes=window_minutes)

        results = []
        for ev in self.events:
            if currency and ev.currency != currency:
                continue
            if ev.is_released and start_time <= ev.timestamp <= now:
                results.append(ev)

        return results
