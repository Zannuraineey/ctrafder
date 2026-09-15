"""
Main Entrypoint for AI Multi-Market Trading Intelligence Engine.
Provides unified CLI for live trading, backtesting, model training, and emergency halt.
"""

import sys
from typing import Optional, List, Dict
import asyncio
from datetime import datetime, timedelta
import typer
from rich.console import Console
from rich.live import Live
from rich.layout import Layout
from rich.table import Table
from rich.panel import Panel
from loguru import logger
import numpy as np

from app.config.settings import get_settings
from app.database import init_db, DatabaseRepository
from app.execution.engine import TradingEngine
from app.broker.models import Candle, SymbolSpecification, Tick
from app.broker.paper_broker import PaperBroker
from app.broker.ctrader.adapter import CTraderBrokerAdapter
from app.broker.ctrader.auth import CTraderAuth
from app.backtest.engine import BacktestEngine
from app.learning.trainer import ModelTrainer
from app.dashboard.terminal_ui import TerminalDashboard
from app.agents.floor import TradingFloor
from app.fundamental.calendar import EconomicCalendar, EventImpact
from app.fundamental.blackout import NewsBlackoutShield
from app.risk.var import ValueAtRiskEngine
from app.risk.covariance import CovarianceEngine
from app.market.deriv_universe import DERIV_UNIVERSE_CATALOG, AccountTier, DerivUniverseRegistry
from app.risk.account_tier import AccountTierEngine
from app.learning.mistake_engine import MistakeEngine, MistakeType

app = typer.Typer(
    help="AI Multi-Market Trading Intelligence Engine for Deriv cTrader",
    add_completion=False,
)
console = Console()


def configure_logging():
    """Configure loguru format and file sink."""
    settings = get_settings()
    logger.remove()
    logger.add(
        sys.stderr,
        level=settings.log_level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <7}</level> | <cyan>{message}</cyan>",
    )
    logger.add("logs/trading.log", rotation="20 MB", retention="10 days", level="DEBUG")


def generate_synthetic_candles(symbol: str, count: int = 300, base_price: float = 2350.0) -> list[Candle]:
    """Generate realistic candle series for simulation/backtest testing."""
    candles = []
    curr = base_price
    now = datetime.utcnow() - timedelta(minutes=count)

    np.random.seed(42)
    for i in range(count):
        ret = np.random.normal(0.0001, 0.0015)
        curr = max(1.0, curr * (1.0 + ret))
        noise = curr * 0.0008
        o = curr - noise * 0.4
        c = curr + noise * 0.5
        h = max(o, c) + abs(np.random.normal(0, noise * 0.6))
        l = min(o, c) - abs(np.random.normal(0, noise * 0.6))
        ts = now + timedelta(minutes=i)
        candles.append(
            Candle(
                symbol=symbol,
                timeframe="1m",
                timestamp=ts,
                open=round(o, 2),
                high=round(h, 2),
                low=round(l, 2),
                close=round(c, 2),
                volume=float(np.random.randint(50, 500)),
            )
        )
    return candles


@app.command()
def run(
    mode: str = typer.Option("paper", "--mode", "-m", help="Trading mode: paper | demo | live"),
    cycles: int = typer.Option(0, "--cycles", "-c", help="Limit execution cycles (0 for indefinite)"),
):
    """
    Launch the AI Multi-Market Trading Engine.
    """
    configure_logging()
    init_db()
    settings = get_settings()
    settings.trading_mode = mode

    console.print(f"[bold green]Starting AI Trading Engine in [{mode.upper()}] mode...[/bold green]")

    async def _async_run():
        broker = PaperBroker(settings) if mode == "paper" else CTraderBrokerAdapter(settings)
        engine = TradingEngine(broker=broker, settings=settings)
        dashboard = TerminalDashboard(console)

        await engine.start()

        # Seed market buffers with initial synthetic historical candles for testing
        symbols = await broker.get_symbols()
        for s in symbols:
            base_p = 2350.0 if "XAU" in s.symbol else 1.0850 if "EUR" in s.symbol else 65000.0 if "BTC" in s.symbol else 1500.0
            test_candles = generate_synthetic_candles(s.symbol, count=100, base_price=base_p)
            engine.scanner.load_historical_candles(s.symbol, test_candles)

        step = 0
        try:
            with Live(console=console, refresh_per_second=2) as live:
                while True:
                    step += 1
                    # Generate live ticks for paper broker simulation
                    for s in symbols:
                        last_c = engine.scanner.buffers_1m[s.symbol].candles[-1] if engine.scanner.buffers_1m[s.symbol].candles else None
                        base_p = last_c.close if last_c else 2350.0
                        tick_noise = base_p * np.random.normal(0, 0.0003)
                        bid = round(base_p + tick_noise, s.digits)
                        ask = round(bid + (s.tick_size * 8), s.digits)
                        sim_tick = Tick(symbol=s.symbol, bid=bid, ask=ask)
                        if isinstance(broker, PaperBroker):
                            broker.update_tick(sim_tick)
                        else:
                            engine.on_tick_received(sim_tick)

                    # Render Dashboard layout
                    layout = Layout()
                    layout.split(
                        Layout(dashboard.generate_account_panel(engine.account_info), size=8),
                        Layout(dashboard.generate_scanner_table(engine.latest_opportunities), size=12),
                        Layout(dashboard.generate_positions_table(await broker.get_open_positions()), size=8),
                    )
                    live.update(layout)

                    await asyncio.sleep(1.0)
                    if cycles > 0 and step >= cycles:
                        break
        except KeyboardInterrupt:
            console.print("\n[yellow]Keyboard interrupt received. Shutting down gracefully...[/yellow]")
        finally:
            await engine.stop()

    asyncio.run(_async_run())


@app.command()
def backtest(
    symbol: str = typer.Option("XAUUSD", "--symbol", "-s", help="Symbol to backtest"),
    bars: int = typer.Option(500, "--bars", "-b", help="Historical bars count"),
):
    """
    Execute an event-driven backtest with realistic spreads, slippage, and deterministic risk.
    """
    configure_logging()
    init_db()
    console.print(f"[bold cyan]Running Event-Driven Backtest for {symbol} ({bars} bars)...[/bold cyan]")

    candles = generate_synthetic_candles(symbol, count=bars, base_price=2350.0 if "XAU" in symbol else 100.0)
    spec = SymbolSpecification(
        symbol=symbol,
        digits=2,
        lot_min=0.01,
        lot_max=20.0,
        lot_step=0.01,
        contract_size=100.0,
        tick_size=0.01,
        tick_value=1.0,
    )

    engine = BacktestEngine(starting_balance=10000.0)
    result = engine.run(candles, spec=spec)
    metrics = result["metrics"]

    table = Table(title=f"BACKTEST RESULTS: {symbol}")
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right", style="cyan")

    table.add_row("Total Trades", str(metrics["total_trades"]))
    table.add_row("Win Rate", f"{metrics['win_rate']*100:.1f}%")
    table.add_row("Profit Factor", f"{metrics['profit_factor']:.2f}")
    table.add_row("Net Profit", f"${metrics['net_profit']:+,.2f} ({metrics['return_pct']:+.1f}%)")
    table.add_row("Expectancy", f"${metrics['expectancy']:+,.2f}")
    table.add_row("Max Drawdown", f"{metrics['max_drawdown_pct']:.2f}%")
    table.add_row("Sharpe Ratio", f"{metrics['sharpe_ratio']:.2f}")
    table.add_row("Sortino Ratio", f"{metrics['sortino_ratio']:.2f}")

    console.print(table)


@app.command()
def train(
    symbol: str = typer.Option("XAUUSD", "--symbol", "-s", help="Symbol for training data"),
    bars: int = typer.Option(600, "--bars", "-b", help="Bars for training data"),
):
    """
    Train machine learning models (Random Forest & Gradient Boosting) using double-barrier labeling.
    """
    configure_logging()
    init_db()
    console.print(f"[bold green]Training ML Models on {symbol} ({bars} bars)...[/bold green]")

    candles = generate_synthetic_candles(symbol, count=bars)
    results = ModelTrainer.train_models_on_candles(candles)

    console.print("[bold green]Training Completed Successfully:[/bold green]")
    for model_name, metrics in results.items():
        console.print(f"  • [cyan]{model_name}[/cyan]: {metrics}")


@app.command()
def status():
    """
    Display SQLite database stats and historical journal performance.
    """
    init_db()
    stats = DatabaseRepository.get_trade_stats()
    console.print(Panel(
        f"[bold]Total Recorded Trades:[/bold] {stats['total_trades']}\n"
        f"[bold]Wins:[/bold] {stats['wins']}  |  [bold]Losses:[/bold] {stats['losses']}\n"
        f"[bold]Win Rate:[/bold] {stats['win_rate']*100:.1f}%\n"
        f"[bold]Profit Factor:[/bold] {stats['profit_factor']:.2f}\n"
        f"[bold]Total Realized P&L:[/bold] ${stats['total_pnl']:+,.2f}\n"
        f"[bold]Average Duration:[/bold] {stats['avg_duration']} seconds",
        title="DATABASE JOURNAL PERFORMANCE",
        border_style="green",
    ))


@app.command()
def authorize(
    redirect_uri: str = typer.Option("http://localhost:8080/callback", "--redirect-uri", "-r", help="Redirect URI registered in openapi.ctrader.com"),
    code: Optional[str] = typer.Option(None, "--code", "-c", help="OAuth authorization code"),
    token: Optional[str] = typer.Option(None, "--token", "-t", help="Direct access token"),
):
    """
    Generate Spotware cTrader Open API OAuth 2.0 authorization URL or exchange tokens.
    """
    from scripts.authorize_ctrader import update_env
    settings = get_settings()
    auth = CTraderAuth(settings)

    if token:
        update_env("CTRADER_ACCESS_TOKEN", token)
        console.print(f"[bold green]Saved CTRADER_ACCESS_TOKEN to .env[/bold green]")
        try:
            accounts = auth.get_trading_accounts(token)
            acc_list = accounts if isinstance(accounts, list) else accounts.get("data", [])
            for acc in acc_list:
                aid = acc.get("accountId") or acc.get("accountNumber")
                is_live = acc.get("live", False)
                console.print(f"  • Account ID: [cyan]{aid}[/cyan] (Live: {is_live}, Broker: {acc.get('brokerName')})")
            if acc_list:
                first_id = str(acc_list[0].get("accountId") or acc_list[0].get("accountNumber"))
                update_env("CTRADER_ACCOUNT_ID", first_id)
                update_env("CTRADER_ENVIRONMENT", "live" if acc_list[0].get("live") else "demo")
                console.print(f"[bold green]Configured primary Account ID: {first_id}[/bold green]")
        except Exception as e:
            console.print(f"[yellow]Could not fetch account list automatically: {e}[/yellow]")
        return

    if code:
        console.print("[cyan]Exchanging authorization code for tokens...[/cyan]")
        try:
            tokens = auth.exchange_code_for_token(code=code, redirect_uri=redirect_uri)
            acc_tok = tokens.get("accessToken") or tokens.get("access_token", "")
            ref_tok = tokens.get("refreshToken") or tokens.get("refresh_token", "")
            if acc_tok:
                update_env("CTRADER_ACCESS_TOKEN", acc_tok)
                console.print("[bold green]Saved CTRADER_ACCESS_TOKEN to .env[/bold green]")
            if ref_tok:
                update_env("CTRADER_REFRESH_TOKEN", ref_tok)
                console.print("[bold green]Saved CTRADER_REFRESH_TOKEN to .env[/bold green]")
        except Exception as e:
            console.print(f"[bold red]Token exchange failed: {e}[/bold red]")
        return

    url = auth.get_authorization_url(redirect_uri=redirect_uri)
    console.print(f"[bold cyan]Visit this link in your browser to authorize cTrader:[/bold cyan]\n[green]{url}[/green]\n")
    console.print("[yellow]Tip: Run 'python scripts/authorize_ctrader.py' for interactive 1-step account pairing.[/yellow]")



@app.command(name="emergency-stop")
def emergency_stop():
    """
    Trigger emergency kill switch: closes all positions and halts execution.
    """
    configure_logging()
    init_db()
    settings = get_settings()
    broker = PaperBroker(settings) if settings.trading_mode == "paper" else CTraderBrokerAdapter(settings)
    engine = TradingEngine(broker=broker, settings=settings)

    async def _async_stop():
        await broker.connect()
        await engine.emergency_stop()
        await broker.disconnect()

@app.command(name="floor-status")
def floor_status():
    """
    Display the 100-Trader Multi-Agent Pod Floor architecture and performance allocation.
    """
    init_db()
    floor = TradingFloor()
    summary = floor.get_pod_summary()

    table = Table(title="[bold yellow]THE 100-TRADER MULTI-AGENT FLOOR (POD SUMMARY)[/bold yellow]")
    table.add_column("Pod Name", style="cyan")
    table.add_column("Traders Count", justify="center")
    table.add_column("Total Trades", justify="center")
    table.add_column("Win Rate", justify="right")
    table.add_column("Total Realized PnL", justify="right")
    table.add_column("Avg Capital Multiplier", justify="right", style="green")

    for pod_name, stats in summary.items():
        pnl_color = "green" if stats["pnl"] >= 0 else "red"
        table.add_row(
            pod_name,
            str(stats["agent_count"]),
            str(stats["total_trades"]),
            f"{stats['win_rate']*100:.1f}%",
            f"[{pnl_color}]${stats['pnl']:+,.2f}[/{pnl_color}]",
            f"{stats['avg_weight']:.2f}x",
        )

    console.print(table)


@app.command(name="macro")
def macro(window_hours: int = typer.Option(24, "--window", "-w", help="Hours to scan ahead")):
    """
    Display Economic Calendar releases, impact levels, and active News Blackout Shields.
    """
    calendar = EconomicCalendar()
    events = calendar.get_upcoming_events(window_minutes=window_hours * 60, min_impact=EventImpact.MEDIUM)
    shield = NewsBlackoutShield(calendar=calendar)

    table = Table(title="[bold magenta]MACROECONOMIC CALENDAR & EVENT DEFENSE SHIELD[/bold magenta]")
    table.add_column("Time (UTC)", style="dim")
    table.add_column("Currency", justify="center", style="bold")
    table.add_column("Impact", justify="center")
    table.add_column("Event Title", style="cyan")
    table.add_column("Forecast", justify="right")
    table.add_column("Previous", justify="right")

    for ev in events:
        impact_color = "red" if ev.impact == EventImpact.HIGH else "yellow"
        time_str = ev.timestamp.strftime("%Y-%m-%d %H:%M")
        table.add_row(
            time_str,
            ev.currency,
            f"[{impact_color}]{ev.impact.value}[/{impact_color}]",
            ev.title,
            f"{ev.forecast} {ev.unit}" if ev.forecast is not None else "-",
            f"{ev.previous} {ev.unit}" if ev.previous is not None else "-",
        )

    console.print(table)

    # Check current blackout status for major assets
    assets = ["XAUUSD", "EURUSD", "GBPUSD", "US100", "Vol_15_1s"]
    shield_table = Table(title="[bold red]NEWS BLACKOUT STATUS (SPREAD DEFENSE)[/bold red]")
    shield_table.add_column("Symbol", style="cyan")
    shield_table.add_column("Shield Status", justify="center")
    shield_table.add_column("Reason / Detail")

    for a in assets:
        is_bo, reason = shield.check_blackout(a)
        status_text = "[bold red]BLOCKED[/bold red]" if is_bo else "[bold green]ACTIVE (SAFE)[/bold green]"
        shield_table.add_row(a, status_text, reason or "No high-impact releases in window")

    console.print(shield_table)


@app.command(name="var-report")
def var_report():
    """
    Display 99% Portfolio Value-at-Risk (VaR), Expected Shortfall, and Net Currency Delta exposure.
    """
    init_db()
    broker = PaperBroker()

    async def _async_var():
        await broker.connect()
        positions = await broker.get_open_positions()
        volatilities = {"XAUUSD": 0.18, "EURUSD": 0.08, "BTCUSD": 0.55, "US100": 0.22}
        total_var, cvar = ValueAtRiskEngine.calculate_portfolio_var(positions, volatilities)
        deltas = CovarianceEngine.calculate_net_currency_exposure(positions)

        console.print(Panel(
            f"[bold]Portfolio 99% 1-Day VaR:[/bold] ${total_var:,.2f}\n"
            f"[bold]Expected Shortfall (CVaR):[/bold] ${cvar:,.2f}\n"
            f"[bold]Open Positions Count:[/bold] {len(positions)}",
            title="[bold red]INSTITUTIONAL RISK & VALUE-AT-RISK (VAR)[/bold red]",
            border_style="red",
        ))

        delta_table = Table(title="[bold cyan]NET CURRENCY DELTA EXPOSURE[/bold cyan]")
        delta_table.add_column("Currency / Asset", style="bold")
        delta_table.add_column("Net Lots Exposure", justify="right")
        delta_table.add_column("Delta Status", justify="center")

        for curr, lots in deltas.items():
            color = "green" if lots > 0 else "red" if lots < 0 else "dim"
            status = "NET LONG" if lots > 0 else "NET SHORT" if lots < 0 else "FLAT"
            delta_table.add_row(curr, f"[{color}]{lots:+.2f} lots[/{color}]", status)

        console.print(delta_table)
        await broker.disconnect()

    asyncio.run(_async_var())


@app.command(name="symbols-catalog")
def symbols_catalog(
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Filter by asset class (SYNTHETIC, METALS, FOREX, COMMODITIES, CRYPTO)"),
    tier: Optional[str] = typer.Option(None, "--tier", "-t", help="Filter by max tier (MICRO, SMALL, MEDIUM, INSTITUTIONAL)"),
):
    """
    Display the complete Deriv & cTrader asset catalog (~50+ symbols), specs, and risk ratings.
    """
    table = Table(title="[bold yellow]DERIV & CTRADER ASSET CATALOG (~50+ INSTRUMENTS)[/bold yellow]")
    table.add_column("Symbol", style="bold cyan")
    table.add_column("Asset Class", justify="center")
    table.add_column("Min Lot", justify="right")
    table.add_column("Min Risk ($)", justify="right", style="bold")
    table.add_column("Account Tier", justify="center")
    table.add_column("Volatility", justify="center")
    table.add_column("Blowout Risk / Sizing Notes")

    for sym, meta in DERIV_UNIVERSE_CATALOG.items():
        if category and meta.spec.asset_class.upper() != category.upper():
            continue
        if tier and meta.tier.value.upper() != tier.upper():
            continue

        min_risk = AccountTierEngine.calculate_minimum_dollar_risk(meta.spec)
        tier_color = "green" if meta.tier == AccountTier.MICRO else "yellow" if meta.tier == AccountTier.SMALL else "magenta" if meta.tier == AccountTier.MEDIUM else "red"
        vol_color = "green" if meta.volatility_rating == "LOW" else "yellow" if meta.volatility_rating == "MEDIUM" else "red"

        table.add_row(
            sym,
            meta.spec.asset_class,
            f"{meta.spec.lot_min:.3g}",
            f"${min_risk:.2f}",
            f"[{tier_color}]{meta.tier.value}[/{tier_color}]",
            f"[{vol_color}]{meta.volatility_rating}[/{vol_color}]",
            meta.blowout_risk_notes,
        )

    console.print(table)


@app.command(name="small-account-advice")
def small_account_advice(
    balance: float = typer.Option(50.0, "--balance", "-b", help="Account balance in USD"),
):
    """
    Generate an institutional sizing & safety advisory report for small accounts ($10–$500).
    """
    account_tier = AccountTierEngine.classify_account(balance)
    max_risk_2pct = balance * 0.02
    max_risk_1pct = balance * 0.01

    console.print(Panel(
        f"[bold]Account Balance:[/bold] ${balance:,.2f}  |  [bold]Classified Tier:[/bold] [bold cyan]{account_tier.value}[/bold cyan]\n"
        f"[bold]1% Risk Budget:[/bold] ${max_risk_1pct:.2f}  |  [bold]2% Max Risk Limit:[/bold] ${max_risk_2pct:.2f}\n"
        f"[dim]The #1 cause of small account blowouts on Deriv is trading symbols with minimum dollar losses exceeding 10-25% of account balance.[/dim]",
        title="[bold green]INSTITUTIONAL SMALL ACCOUNT ADVISORY ENGINE[/bold green]",
        border_style="green",
    ))

    # Evaluate all instruments
    approved = []
    forbidden = []

    for sym, meta in DERIV_UNIVERSE_CATALOG.items():
        verdict = AccountTierEngine.evaluate_symbol_feasibility(meta.spec, balance=balance)
        if verdict.is_safe:
            approved.append((meta, verdict))
        else:
            forbidden.append((meta, verdict))

    # 1. Approved Table
    safe_table = Table(title=f"[bold green]APPROVED PAIRS FOR ${balance:.0f} ACCOUNT ({len(approved)} INSTRUMENTS)[/bold green]")
    safe_table.add_column("Symbol", style="bold green")
    safe_table.add_column("Min Lot", justify="right")
    safe_table.add_column("Min Dollar Risk", justify="right")
    safe_table.add_column("% of Account", justify="right")
    safe_table.add_column("Why It Is Safe")

    for meta, v in approved:
        safe_table.add_row(
            meta.spec.symbol,
            f"{meta.spec.lot_min:.3g}",
            f"${v.min_dollar_risk:.2f}",
            f"{v.risk_percentage_of_account:.1f}%",
            meta.blowout_risk_notes,
        )
    console.print(safe_table)

    # 2. Forbidden Table
    danger_table = Table(title=f"[bold red]FORBIDDEN HIGH-RISK PAIRS (BLOWOUT VETOED)[/bold red]")
    danger_table.add_column("Symbol", style="bold red")
    danger_table.add_column("Min Dollar Risk", justify="right")
    danger_table.add_column("Blowout Risk %", justify="right", style="bold red")
    danger_table.add_column("Veto Reason")

    for meta, v in forbidden[:10]:  # Show top 10 most prominent
        danger_table.add_row(
            meta.spec.symbol,
            f"${v.min_dollar_risk:.2f}",
            f"{v.risk_percentage_of_account:.1f}% of balance",
            v.veto_reason or "Account tier mismatch",
        )
    console.print(danger_table)


@app.command(name="mistakes-report")
def mistakes_report():
    """
    Display post-mortem failure diagnostics, anti-greed penalties, and blowouts prevented.
    """
    init_db()
    summary = DatabaseRepository.get_mistakes_summary()
    recent = DatabaseRepository.get_recent_mistakes(limit=15)

    console.print(Panel(
        f"[bold]Total Recorded Mistakes Intercepted:[/bold] {summary['total_mistakes']}\n"
        f"[bold]Estimated Capital Protected / Losses Avoided:[/bold] ${summary['total_loss_amount']:,.2f}\n"
        f"[bold]Mistake Breakdown:[/bold] {summary['breakdown']}",
        title="[bold yellow]POST-MORTEM FAILURE LEARNING & ANTI-GREED REPORT[/bold yellow]",
        border_style="yellow",
    ))

    if recent:
        table = Table(title="RECENT MISTAKES INTERCEPTED & AGENTS BENCHED")
        table.add_column("Timestamp", style="dim")
        table.add_column("Symbol", style="bold cyan")
        table.add_column("Agent ID", justify="center")
        table.add_column("Mistake Type", style="bold red")
        table.add_column("Action Taken", justify="center")
        table.add_column("Details")

        for m in recent:
            time_str = m["timestamp"].strftime("%Y-%m-%d %H:%M")
            table.add_row(
                time_str,
                m["symbol"],
                str(m["agent_id"]) if m["agent_id"] else "-",
                m["mistake_type"],
                m["action_taken"],
                m["details"],
            )
@app.command(name="dashboard")
def dashboard(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Dashboard host"),
    port: int = typer.Option(8000, "--port", "-p", help="Dashboard port"),
):
    """
    Launch the Institutional Quantitative Trading Workstation (Web Dashboard).
    """
    init_db()
    console.print(f"[bold green]Starting Institutional Trading Workstation at http://{host}:{port}[/bold green]")
    console.print(f"[cyan]Features 100-Agent Floor Matrix, Deriv 57 Sizing Filter, Order Flow Canvas, and Anti-Greed Logs.[/cyan]")
    from app.dashboard.server import run_dashboard_server
    run_dashboard_server(host=host, port=port)


if __name__ == "__main__":
    app()


