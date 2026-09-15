"""
Order Manager: Dispatches risk-approved trades to broker adapter.
Section 37 and 74 of project.md.
"""

from typing import Optional
from loguru import logger

from app.broker.base import BrokerAdapter
from app.broker.models import RiskDecisionObject, Order, TradeSide


class OrderManager:
    """
    Executes approved trades and manages order lifecycle.
    """

    def __init__(self, broker: BrokerAdapter):
        self.broker = broker

    async def execute_approved_trade(
        self, decision: RiskDecisionObject, strategy_name: str = ""
    ) -> Optional[Order]:
        """
        Submit order to broker if and only if approved by the Risk Engine.
        """
        if not decision.approved or decision.side is None:
            logger.warning(
                f"Attempted to execute unapproved trade on {decision.symbol}: {decision.veto_reason}"
            )
            return None

        try:
            logger.info(
                f"[ORDER DISPATCH] Submitting {decision.symbol} {decision.side.value} "
                f"{decision.volume_lots} lots @ {decision.entry}, SL: {decision.stop_loss}, TP: {decision.take_profit}"
            )
            order = await self.broker.send_market_order(
                symbol=decision.symbol,
                side=decision.side,
                volume_lots=decision.volume_lots,
                stop_loss=decision.stop_loss,
                take_profit=decision.take_profit,
                comment=strategy_name,
            )
            return order
        except Exception as e:
            logger.error(f"Failed to submit order for {decision.symbol}: {e}")
            return None
