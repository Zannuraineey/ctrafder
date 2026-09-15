"""
Execution Analytics & Slippage Tracking Engine.
Measures fill latency, implementation shortfall, slippage distributions,
and execution transaction costs per asset class.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import numpy as np
from loguru import logger

from app.broker.models import TradeSide, SymbolSpecification


@dataclass
class ExecutionFillMetric:
    trade_id: str
    symbol: str
    side: TradeSide
    requested_price: float
    executed_price: float
    slippage: float             # In price units (positive = adverse slippage, negative = price improvement)
    slippage_pips: float
    slippage_dollar: float
    latency_ms: float
    spread_cost_dollar: float
    fill_time: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ExecutionQualitySummary:
    total_fills: int
    avg_slippage_pips: float
    adverse_slippage_ratio: float  # Percentage of fills with negative slippage
    p50_latency_ms: float
    p95_latency_ms: float
    total_slippage_cost_usd: float
    total_spread_cost_usd: float


class ExecutionAnalyticsEngine:
    """
    Quantitative analyzer tracking execution quality, venue latency,
    and adverse fill slippage.
    """

    def __init__(self):
        self.fills: List[ExecutionFillMetric] = []
        self._symbol_slippage_history: Dict[str, List[float]] = {}

    def record_fill(
        self,
        trade_id: str,
        symbol: str,
        side: TradeSide,
        requested_price: float,
        executed_price: float,
        spec: SymbolSpecification,
        lots: float,
        signal_timestamp: datetime,
        fill_timestamp: datetime,
        current_spread: float,
    ) -> ExecutionFillMetric:
        """
        Record and analyze order fill metrics.
        """
        latency_ms = max(0.0, (fill_timestamp - signal_timestamp).total_seconds() * 1000.0)

        # Slippage: for BUY, higher execution is adverse; for SELL, lower execution is adverse
        if side == TradeSide.BUY:
            raw_slip = executed_price - requested_price
        else:
            raw_slip = requested_price - executed_price

        # Convert to pips
        pip_size = spec.tick_size * 10.0 if spec.digits in (3, 5) else spec.tick_size
        slip_pips = raw_slip / max(pip_size, 1e-9)

        # Dollar impact: lots * contract_size * raw_slip
        dollar_slip = lots * spec.contract_size * raw_slip
        spread_cost = lots * spec.contract_size * (current_spread * 0.5)

        metric = ExecutionFillMetric(
            trade_id=trade_id,
            symbol=symbol,
            side=side,
            requested_price=requested_price,
            executed_price=executed_price,
            slippage=round(raw_slip, 6),
            slippage_pips=round(slip_pips, 2),
            slippage_dollar=round(dollar_slip, 2),
            latency_ms=round(latency_ms, 2),
            spread_cost_dollar=round(spread_cost, 2),
            fill_time=fill_timestamp,
        )

        self.fills.append(metric)
        self._symbol_slippage_history.setdefault(symbol, []).append(slip_pips)

        logger.info(
            f"[EXECUTION FILL] {symbol} {side.value} Lots: {lots:.2f} | Slip: {slip_pips:+.1f} pips "
            f"(${dollar_slip:+.2f}) | Latency: {latency_ms:.1f}ms"
        )
        return metric

    def get_quality_summary(self, symbol: Optional[str] = None) -> ExecutionQualitySummary:
        """
        Compute aggregate execution statistics for the portfolio or a specific symbol.
        """
        selected_fills = (
            [f for f in self.fills if f.symbol == symbol]
            if symbol
            else self.fills
        )

        if not selected_fills:
            return ExecutionQualitySummary(
                total_fills=0,
                avg_slippage_pips=0.0,
                adverse_slippage_ratio=0.0,
                p50_latency_ms=0.0,
                p95_latency_ms=0.0,
                total_slippage_cost_usd=0.0,
                total_spread_cost_usd=0.0,
            )

        slip_pips = [f.slippage_pips for f in selected_fills]
        latencies = [f.latency_ms for f in selected_fills]
        total_slip_cost = sum(f.slippage_dollar for f in selected_fills)
        total_spread_cost = sum(f.spread_cost_dollar for f in selected_fills)

        adverse_count = sum(1 for s in slip_pips if s > 0.1)
        adverse_ratio = adverse_count / len(selected_fills)

        return ExecutionQualitySummary(
            total_fills=len(selected_fills),
            avg_slippage_pips=round(float(np.mean(slip_pips)), 2),
            adverse_slippage_ratio=round(adverse_ratio, 3),
            p50_latency_ms=round(float(np.percentile(latencies, 50)), 1),
            p95_latency_ms=round(float(np.percentile(latencies, 95)), 1),
            total_slippage_cost_usd=round(total_slip_cost, 2),
            total_spread_cost_usd=round(total_spread_cost, 2),
        )
