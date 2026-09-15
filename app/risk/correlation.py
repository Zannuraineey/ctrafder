"""
Correlation Management.
Prevents stacking highly correlated directional risks simultaneously.
"""

from typing import List, Optional, Dict, Set
from app.broker.models import Position, TradeSide, PositionStatus

# Known asset correlation clusters
CORRELATION_CLUSTERS: Dict[str, Set[str]] = {
    "USD_BULL": {"EURUSD:SELL", "GBPUSD:SELL", "USDJPY:BUY", "USDCAD:BUY", "USDCHF:BUY"},
    "USD_BEAR": {"EURUSD:BUY", "GBPUSD:BUY", "USDJPY:SELL", "USDCAD:SELL", "USDCHF:SELL"},
    "GOLD_LONG": {"XAUUSD:BUY", "XAGUSD:BUY"},
    "GOLD_SHORT": {"XAUUSD:SELL", "XAGUSD:SELL"},
    "US_INDICES_LONG": {"US100:BUY", "US30:BUY", "US500:BUY", "NAS100:BUY"},
    "CRYPTO_LONG": {"BTCUSD:BUY", "ETHUSD:BUY"},
}


class CorrelationManager:
    """
    Evaluates proposed trades against active positions to prevent correlated risk clustering.
    """

    def __init__(self, max_cluster_positions: int = 1):
        self.max_cluster_positions = max_cluster_positions

    def check_correlation(
        self,
        symbol: str,
        side: TradeSide,
        open_positions: List[Position],
    ) -> Optional[str]:
        proposed_key = f"{symbol}:{side.value}"
        active_keys = [
            f"{p.symbol}:{p.side.value}"
            for p in open_positions
            if p.status == PositionStatus.OPEN
        ]

        for cluster_name, cluster_set in CORRELATION_CLUSTERS.items():
            if proposed_key in cluster_set:
                matching_active = [k for k in active_keys if k in cluster_set]
                if len(matching_active) >= self.max_cluster_positions:
                    return (
                        f"Correlation veto: cluster '{cluster_name}' already exposed with {matching_active}"
                    )

        return None
