"""
Real-time Candle Buffers and Multi-Timeframe Resampler.
Section 10 and 11 of project.md.
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
from collections import deque
import pandas as pd
from loguru import logger

from app.broker.models import Candle, Tick


class CandleBuffer:
    """
    Fixed-size sliding window buffer of completed and in-progress candles for a symbol.
    """

    def __init__(self, symbol: str, timeframe: str = "1m", maxlen: int = 500):
        self.symbol = symbol
        self.timeframe = timeframe
        self.maxlen = maxlen
        self.candles: deque[Candle] = deque(maxlen=maxlen)
        self.current_candle: Optional[Candle] = None
        self._interval_seconds = self._parse_timeframe_to_seconds(timeframe)

    @staticmethod
    def _parse_timeframe_to_seconds(tf: str) -> int:
        tf = tf.lower()
        if tf == "1m":
            return 60
        elif tf == "5m":
            return 300
        elif tf == "15m":
            return 900
        elif tf == "1h":
            return 3600
        return 60

    def add_candle(self, candle: Candle) -> None:
        """Append a completed historical or finalized candle."""
        self.candles.append(candle)

    def add_candles_bulk(self, candles: List[Candle]) -> None:
        for c in candles:
            self.candles.append(c)

    def on_tick(self, tick: Tick) -> Optional[Candle]:
        """
        Ingest real-time tick, updating current candle or finalizing completed candle.
        Returns newly completed Candle if an interval rollover just happened.
        """
        price = tick.mid
        tick_time = tick.timestamp

        # Calculate interval start
        epoch = datetime(1970, 1, 1)
        total_seconds = int((tick_time - epoch).total_seconds())
        interval_start_seconds = total_seconds - (total_seconds % self._interval_seconds)
        candle_start = epoch + timedelta(seconds=interval_start_seconds)

        completed: Optional[Candle] = None

        if self.current_candle is None:
            self.current_candle = Candle(
                symbol=self.symbol,
                timeframe=self.timeframe,
                timestamp=candle_start,
                open=price,
                high=price,
                low=price,
                close=price,
                volume=1.0,
            )
        elif candle_start > self.current_candle.timestamp:
            # Previous candle is completed
            completed = self.current_candle
            self.candles.append(completed)

            # Start new candle
            self.current_candle = Candle(
                symbol=self.symbol,
                timeframe=self.timeframe,
                timestamp=candle_start,
                open=price,
                high=price,
                low=price,
                close=price,
                volume=1.0,
            )
        else:
            # Update current in-progress candle
            c = self.current_candle
            c.high = max(c.high, price)
            c.low = min(c.low, price)
            c.close = price
            c.volume += 1.0

        return completed

    def get_all_candles(self, include_current: bool = True) -> List[Candle]:
        """Return list of candles, optionally including current active forming candle."""
        res = list(self.candles)
        if include_current and self.current_candle:
            res.append(self.current_candle)
        return res
