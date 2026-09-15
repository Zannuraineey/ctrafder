"""
Terminal Dashboard built with Rich.
Sections 54, 55, and 56 of project.md.
"""

from typing import List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text

from app.broker.models import AccountInfo, Position, MarketRegime
from app.market.scanner import MarketOpportunity


class TerminalDashboard:
    """
    Renders live multi-market trading metrics, account health, and scanner grid in terminal.
    """

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()

    def generate_account_panel(self, account: Optional[AccountInfo], max_daily_loss_pct: float = 0.02) -> Panel:
        if not account:
            return Panel("[yellow]Connecting to Broker...[/yellow]", title="ACCOUNT STATUS")

        daily_loss_limit = account.balance * max_daily_loss_pct
        pnl_color = "green" if account.daily_pnl >= 0 else "red"

        text = Text()
        text.append(f"Account: ", style="bold")
        text.append(f"{account.account_id} ({account.broker})\n")
        text.append(f"Balance: ", style="bold")
        text.append(f"${account.balance:,.2f}  |  ")
        text.append(f"Equity: ", style="bold")
        text.append(f"${account.equity:,.2f}\n")
        text.append(f"Daily P/L: ", style="bold")
        text.append(f"${account.daily_pnl:+,.2f}", style=f"bold {pnl_color}")
        text.append(f"  |  Daily Loss Limit: -${daily_loss_limit:,.2f}\n")
        text.append(f"Free Margin: ", style="bold")
        text.append(f"${account.free_margin:,.2f}  |  Margin Level: {account.margin_level or 999.0:.1f}%\n")
        text.append(f"Open Positions: ", style="bold")
        text.append(f"{account.open_positions_count}")

        return Panel(text, title="[bold cyan]ACCOUNT & RISK SUMMARY[/bold cyan]", border_style="cyan")

    def generate_scanner_table(self, opportunities: List[MarketOpportunity]) -> Table:
        table = Table(title="[bold yellow]MULTI-MARKET SCANNER & OPPORTUNITY RANKING[/bold yellow]")
        table.add_column("Rank", justify="center", style="bold")
        table.add_column("Symbol", style="cyan")
        table.add_column("Regime", justify="center")
        table.add_column("Signal", justify="center", style="bold")
        table.add_column("Win Prob", justify="right")
        table.add_column("Quality", justify="right")
        table.add_column("Whipsaw", justify="right")
        table.add_column("R:R", justify="right")
        table.add_column("Strategy", style="dim")

        if not opportunities:
            table.add_row("-", "Scanning active markets...", "-", "-", "-", "-", "-", "-", "-")
            return table

        for idx, opp in enumerate(opportunities[:10], start=1):
            side_str = opp.signal.side.value if opp.signal.side else "HOLD"
            side_color = "green" if side_str == "BUY" else "red" if side_str == "SELL" else "yellow"

            regime_str = opp.ai_decision.regime.value
            win_prob = max(opp.ai_decision.buy_probability, opp.ai_decision.sell_probability)
            whipsaw_str = f"{opp.ai_decision.whipsaw_probability*100:.0f}%"
            whip_color = "red" if opp.ai_decision.whipsaw_probability > 0.35 else "green"

            table.add_row(
                str(idx),
                opp.symbol,
                regime_str,
                f"[{side_color}]{side_str}[/{side_color}]",
                f"{win_prob*100:.1f}%",
                f"{opp.ai_decision.trade_quality*100:.1f}%",
                f"[{whip_color}]{whipsaw_str}[/{whip_color}]",
                f"{opp.ai_decision.expected_rr:.1f}",
                opp.signal.strategy,
            )

        return table

    def generate_positions_table(self, positions: List[Position]) -> Table:
        table = Table(title="[bold green]ACTIVE SCALPING POSITIONS[/bold green]")
        table.add_column("ID", style="dim")
        table.add_column("Symbol", style="cyan")
        table.add_column("Side", justify="center")
        table.add_column("Entry", justify="right")
        table.add_column("Current", justify="right")
        table.add_column("SL", justify="right", style="red")
        table.add_column("TP", justify="right", style="green")
        table.add_column("PnL ($)", justify="right", style="bold")
        table.add_column("Duration", justify="center")
        table.add_column("Strategy", style="dim")

        if not positions:
            table.add_row("-", "No active positions", "-", "-", "-", "-", "-", "$0.00", "0s", "-")
            return table

        for p in positions:
            side_color = "green" if p.side.value == "BUY" else "red"
            pnl_color = "green" if p.unrealized_pnl >= 0 else "red"
            table.add_row(
                p.id[:8],
                p.symbol,
                f"[{side_color}]{p.side.value}[/{side_color}]",
                f"{p.entry_price:.4f}",
                f"{p.current_price:.4f}",
                f"{p.stop_loss:.4f}",
                f"{p.take_profit:.4f}",
                f"[{pnl_color}]${p.unrealized_pnl:+.2f}[/{pnl_color}]",
                f"{p.duration_seconds}s",
                p.strategy,
            )

        return table
