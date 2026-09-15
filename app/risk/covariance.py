"""
Cross-Asset Covariance & Net Currency Delta Engine.
Prevents compounding directional currency exposure across multiple symbols.
"""

from typing import List, Dict, Optional
from app.broker.models import Position, PositionStatus, TradeSide


class CovarianceEngine:
    """
    Computes net directional currency delta and prevents correlated currency risk concentration.
    """

    @classmethod
    def calculate_net_currency_exposure(
        cls, open_positions: List[Position]
    ) -> Dict[str, float]:
        """
        Aggregate net directional exposure by currency (USD, EUR, GBP, JPY, GOLD).
        Positive = Net Long, Negative = Net Short (in lots).
        """
        net_exposure: Dict[str, float] = {
            "USD": 0.0,
            "EUR": 0.0,
            "GBP": 0.0,
            "JPY": 0.0,
            "XAU": 0.0,
        }

        for p in open_positions:
            if p.status != PositionStatus.OPEN:
                continue

            sym = p.symbol.upper()
            lots = p.volume / 100000.0 if "EUR" in sym or "GBP" in sym else (p.volume / 100.0 if "XAU" in sym else p.volume)
            dir_sign = 1.0 if p.side == TradeSide.BUY else -1.0

            if "EURUSD" in sym:
                net_exposure["EUR"] += dir_sign * lots
                net_exposure["USD"] -= dir_sign * lots
            elif "GBPUSD" in sym:
                net_exposure["GBP"] += dir_sign * lots
                net_exposure["USD"] -= dir_sign * lots
            elif "USDJPY" in sym:
                net_exposure["USD"] += dir_sign * lots
                net_exposure["JPY"] -= dir_sign * lots
            elif "XAUUSD" in sym:
                net_exposure["XAU"] += dir_sign * lots
                net_exposure["USD"] -= dir_sign * lots

        return net_exposure

    @classmethod
    def check_currency_delta_cap(
        cls,
        symbol: str,
        side: TradeSide,
        proposed_lots: float,
        open_positions: List[Position],
        max_net_currency_lots: float = 3.0,
    ) -> Optional[str]:
        """
        Veto if adding this trade breaches net currency delta limit.
        """
        net_exp = cls.calculate_net_currency_exposure(open_positions)
        sym = symbol.upper()
        dir_sign = 1.0 if side == TradeSide.BUY else -1.0

        # Check USD delta
        usd_change = 0.0
        if "USD" in sym:
            if sym.startswith("USD"):
                usd_change = dir_sign * proposed_lots
            else:
                usd_change = -dir_sign * proposed_lots

        new_usd_net = net_exp["USD"] + usd_change
        if abs(new_usd_net) > max_net_currency_lots:
            return (
                f"Net Currency Delta Exceeded: Proposed {symbol} trade would push net USD exposure "
                f"to {new_usd_net:+.2f} lots (Cap: ±{max_net_currency_lots} lots)"
            )

        return None
