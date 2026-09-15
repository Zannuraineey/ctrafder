"""
Pre-Trade Safety Validators.
Section 38 and 81 of project.md.
"""

from typing import Optional
from app.broker.models import AccountInfo, AIDecisionObject, SymbolSpecification, Tick


class TradeValidators:
    """
    Deterministic rule-based pre-trade sanity checks.
    """

    @staticmethod
    def validate_daily_loss(account: AccountInfo, max_daily_loss_pct: float) -> Optional[str]:
        if account.balance <= 0:
            return "Zero or negative balance"
        max_loss_allowed = account.balance * max_daily_loss_pct
        if account.daily_pnl < -max_loss_allowed:
            return f"Daily loss limit exceeded: Daily PnL (${account.daily_pnl:.2f}) < -${max_loss_allowed:.2f}"
        return None

    @staticmethod
    def validate_drawdown(
        current_equity: float, peak_balance: float, max_drawdown_pct: float
    ) -> Optional[str]:
        if peak_balance <= 0:
            return None
        drawdown = (peak_balance - current_equity) / peak_balance
        if drawdown > max_drawdown_pct:
            return f"Max drawdown exceeded ({drawdown*100:.1f}% > {max_drawdown_pct*100:.1f}%)"
        return None

    @staticmethod
    def validate_spread(
        tick: Tick, spec: SymbolSpecification, max_spread_pips: float
    ) -> Optional[str]:
        pip_size = spec.tick_size * 10 if spec.digits in (2, 3, 5) else spec.tick_size
        spread_pips = tick.spread / max(pip_size, 1e-9)
        if spread_pips > max_spread_pips:
            return f"Spread too wide ({spread_pips:.1f} pips > max {max_spread_pips} pips)"
        return None

    @staticmethod
    def validate_ai_decision(
        ai_decision: AIDecisionObject,
        min_win_prob: float,
        min_quality: float,
        max_whipsaw: float,
        min_rr: float,
    ) -> Optional[str]:
        if ai_decision.direction is None:
            return "AI proposed NO TRADE"

        win_prob = max(ai_decision.buy_probability, ai_decision.sell_probability)
        if win_prob < min_win_prob:
            return f"AI win probability ({win_prob*100:.1f}%) below minimum ({min_win_prob*100:.1f}%)"

        if ai_decision.trade_quality < min_quality:
            return f"AI trade quality ({ai_decision.trade_quality*100:.1f}%) below threshold ({min_quality*100:.1f}%)"

        if ai_decision.whipsaw_probability > max_whipsaw:
            return f"Whipsaw probability ({ai_decision.whipsaw_probability*100:.1f}%) exceeds safety ceiling ({max_whipsaw*100:.1f}%)"

        if ai_decision.expected_rr < min_rr:
            return f"Expected Risk/Reward ({ai_decision.expected_rr}) below required ({min_rr})"

        return None
