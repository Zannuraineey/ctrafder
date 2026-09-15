"""
Base Strategy Interface and Signal candidate definitions.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import pandas as pd

from app.broker.models import TradeSignal, SymbolSpecification, MarketRegime


class BaseStrategy(ABC):
    """Abstract base class for all algorithmic trading strategies."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def evaluate(
        self,
        symbol: str,
        features_df: pd.DataFrame,
        regime: MarketRegime,
        spec: SymbolSpecification,
        higher_tf_features_df: Optional[pd.DataFrame] = None,
    ) -> Optional[TradeSignal]:
        """
        Evaluate candidate setup.
        Returns a TradeSignal if setup criteria are met, otherwise None.
        """
        pass
