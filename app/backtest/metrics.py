"""
Backtest Financial Performance Metrics Calculator.
Section 76 of project.md.
"""

from typing import List, Dict, Any
import numpy as np
import pandas as pd


def calculate_backtest_metrics(trades: List[Dict[str, Any]], starting_balance: float = 10000.0) -> Dict[str, Any]:
    """
    Compute comprehensive quantitative trading metrics.
    """
    if not trades:
        return {
            "total_trades": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "net_profit": 0.0,
            "return_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "expectancy": 0.0,
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
        }

    pnls = [t["profit_loss"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]

    total_trades = len(trades)
    win_count = len(wins)
    loss_count = len(losses)
    win_rate = round(win_count / total_trades, 4)

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    net_profit = round(sum(pnls), 2)
    return_pct = round((net_profit / starting_balance) * 100.0, 2)

    profit_factor = (
        round(gross_profit / gross_loss, 2)
        if gross_loss > 0
        else (999.0 if gross_profit > 0 else 0.0)
    )

    avg_win = round(float(np.mean(wins)), 2) if wins else 0.0
    avg_loss = round(float(np.mean(losses)), 2) if losses else 0.0
    expectancy = round(float(np.mean(pnls)), 2)

    # Equity curve & Max Drawdown
    equity_curve = [starting_balance]
    curr_balance = starting_balance
    for p in pnls:
        curr_balance += p
        equity_curve.append(curr_balance)

    eq_series = pd.Series(equity_curve)
    peak = eq_series.cummax()
    drawdown = (peak - eq_series) / peak
    max_drawdown_pct = round(float(drawdown.max() * 100.0), 2)

    # Sharpe & Sortino
    returns_series = pd.Series(pnls) / starting_balance
    mean_ret = returns_series.mean()
    std_ret = returns_series.std()
    neg_std = returns_series[returns_series < 0].std()

    sharpe = round(float((mean_ret / (std_ret + 1e-9)) * np.sqrt(252)), 2) if std_ret > 0 else 0.0
    sortino = round(float((mean_ret / (neg_std + 1e-9)) * np.sqrt(252)), 2) if neg_std > 0 else 0.0

    return {
        "total_trades": total_trades,
        "wins": win_count,
        "losses": loss_count,
        "win_rate": win_rate,
        "net_profit": net_profit,
        "return_pct": return_pct,
        "profit_factor": profit_factor,
        "expectancy": expectancy,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "max_drawdown_pct": max_drawdown_pct,
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
    }
