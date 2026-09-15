"""
Live Tick & Order Flow Engine for Scalping.
Tracks real-time tick velocity (dp/dt), relative tick activity,
spread efficiency, and Depth of Market (DOM) Level II order book imbalance.
(project.md Sections 1, 4, 6)
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import deque
import numpy as np

from app.broker.models import Tick, SymbolSpecification
from app.scalping.models import TickMetric, DOMQuote


class ScalpTickEngine:
    """
    High-speed micro-tick processor maintaining rolling tick buffers
    and computing tick velocity, activity bursts, and DOM depth pressure.
    """

    def __init__(self, max_buffer_size: int = 60):
        self.max_buffer_size = max_buffer_size
        # symbol -> deque of Tick objects
        self.tick_buffers: Dict[str, deque] = {}
        # symbol -> rolling velocity history for acceleration
        self.velocity_history: Dict[str, deque] = {}
        # symbol -> cached DOM quote
        self.dom_quotes: Dict[str, DOMQuote] = {}

    def ingest_tick(
        self,
        tick: Tick,
        spec: Optional[SymbolSpecification] = None,
        typical_atr: Optional[float] = None,
    ) -> TickMetric:
        """
        Record a live tick and immediately calculate real-time micro-metrics:
        price velocity, acceleration, tick count rate, relative volume, and spread.
        """
        sym = tick.symbol
        if sym not in self.tick_buffers:
            self.tick_buffers[sym] = deque(maxlen=self.max_buffer_size)
            self.velocity_history[sym] = deque(maxlen=10)

        buf = self.tick_buffers[sym]
        buf.append(tick)

        # 1. Spread Calculation
        spread_pts = max(0.0, tick.ask - tick.bid)
        atr = typical_atr if typical_atr and typical_atr > 0 else max(spread_pts * 5.0, 0.001)
        spread_ratio = spread_pts / atr  # Lower is better (< 0.15 is institutional tight)

        # 2. Price Velocity (dp/dt in points per second over last 5-10 ticks)
        velocity = 0.0
        accel = 0.0
        tick_rate = 1.0

        if len(buf) >= 3:
            recent_count = min(len(buf), 8)
            old_tick = buf[-recent_count]
            new_tick = buf[-1]
            dt = (new_tick.timestamp - old_tick.timestamp).total_seconds()
            if dt > 0.05:
                dp = new_tick.mid - old_tick.mid
                velocity = float(dp / dt)
                tick_rate = float(recent_count / dt)
            else:
                velocity = 0.0
                tick_rate = 10.0

            # Acceleration (rate of change of velocity)
            v_hist = self.velocity_history[sym]
            v_hist.append(velocity)
            if len(v_hist) >= 2:
                accel = v_hist[-1] - v_hist[-2]

        # 3. Relative Tick Activity (Recent frequency vs rolling average)
        if len(buf) >= 20:
            total_dt = max(0.1, (buf[-1].timestamp - buf[0].timestamp).total_seconds())
            avg_rate = len(buf) / total_dt
            rel_activity = float(np.clip(tick_rate / max(avg_rate, 0.1), 0.2, 5.0))
        else:
            rel_activity = 1.0

        metric = TickMetric(
            symbol=sym,
            last_price=tick.mid,
            spread_points=spread_pts,
            spread_ratio=spread_ratio,
            velocity_pts_sec=velocity,
            acceleration=accel,
            tick_count_rate=tick_rate,
            relative_activity=rel_activity,
            timestamp=tick.timestamp,
        )

        # Update synthetic or live DOM depth
        self._update_dom_quote(sym, tick, velocity, rel_activity)
        return metric

    def update_dom_quote(self, dom: DOMQuote) -> None:
        """Manually update DOM quote from external cTrader Open API Level II feed."""
        self.dom_quotes[dom.symbol] = dom

    def get_dom_quote(self, symbol: str) -> DOMQuote:
        """Return latest Level II order book depth quote."""
        if symbol in self.dom_quotes:
            return self.dom_quotes[symbol]
        return DOMQuote(symbol=symbol, bid_depth=500.0, ask_depth=500.0)

    def _update_dom_quote(self, symbol: str, tick: Tick, velocity: float, activity: float) -> None:
        """
        Dynamically models DOM depth liquidity walls based on tick momentum
        and price pressure when native Level II feed is simulated.
        """
        base_depth = 500.0 * max(0.5, activity)
        # Positive velocity increases bid-side depth accumulation (buyers stepping up)
        skew = float(np.clip(velocity * 10.0, -0.6, 0.6))
        bid_depth = round(base_depth * (1.0 + skew), 1)
        ask_depth = round(base_depth * (1.0 - skew), 1)

        self.dom_quotes[symbol] = DOMQuote(
            symbol=symbol,
            bid_depth=max(50.0, bid_depth),
            ask_depth=max(50.0, ask_depth),
            timestamp=tick.timestamp,
        )
