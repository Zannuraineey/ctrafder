"""
Symbol Discovery and Instrument Registry.
Section 8 and 9 of project.md.
"""

from typing import Dict, List, Optional
from loguru import logger

from app.broker.models import SymbolSpecification
from app.database.repository import DatabaseRepository


class SymbolRegistry:
    """
    Maintains repository of available trading instruments and contract parameters.
    """

    def __init__(self):
        self._symbols: Dict[str, SymbolSpecification] = {}

    def register_symbol(self, spec: SymbolSpecification) -> None:
        self._symbols[spec.symbol] = spec
        try:
            DatabaseRepository.save_market(spec)
        except Exception:
            pass

    def get_symbol(self, symbol: str) -> Optional[SymbolSpecification]:
        if symbol in self._symbols:
            return self._symbols[symbol]
        db_spec = DatabaseRepository.get_market(symbol)
        if db_spec:
            self._symbols[symbol] = db_spec
            return db_spec
        return None

    def get_all_symbols(self) -> List[SymbolSpecification]:
        if not self._symbols:
            db_symbols = DatabaseRepository.get_all_active_markets()
            for s in db_symbols:
                self._symbols[s.symbol] = s
        return list(self._symbols.values())
