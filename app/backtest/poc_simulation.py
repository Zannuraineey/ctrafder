"""
Multi-Pair POC Paper Trading Simulation Engine.
Runs event-driven paper simulation across all scannable Deriv pairs,
evaluates how price respects the Point of Control (POC),
and calculates/ranks pair profitability to inspect which pair yields the highest profits.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from loguru import logger

from app.broker.models import (
    SymbolSpecification,
    TradeSide,
    ExitReason,
    MarketRegime,
)
from app.market.deriv_universe import DERIV_UNIVERSE_CATALOG, DerivUniverseRegistry
from app.strategies.poc_strategy import POCReactionStrategy, compute_volume_profile


class POCPaperSimulator:
    """
    Simulates paper trading execution of the POC Reaction Strategy across multiple pairs
    to compare and rank their profitability.
    """

    def __init__(
        self,
        starting_balance: float = 100.0,
        risk_per_trade: float = 0.03,  # 3% standard institutional scalp risk
        spread_pips: float = 0.8,
        slippage_pips: float = 0.2,
        commission_per_lot: float = 3.0,
    ):
        self.starting_balance = starting_balance
        self.risk_per_trade = risk_per_trade
        self.spread_pips = spread_pips
        self.slippage_pips = slippage_pips
        self.commission_per_lot = commission_per_lot
        self.strategy = POCReactionStrategy()

    def generate_pair_candles(
        self,
        symbol: str,
        base_price: float,
        count: int = 120,
        seed: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Generate realistic synthetic candle series for paper simulation."""
        meta = DERIV_UNIVERSE_CATALOG.get(symbol)
        digits = meta.spec.digits if meta else 5
        atr = meta.typical_atr_points if meta else max(0.0005, base_price * 0.001)

        rng = np.random.RandomState(seed or (abs(hash(symbol)) % 100000))
        candles = []
        curr_p = base_price
        min_pip = 10 ** (-digits)

        # Generate trending / mean-reverting swing cycles around POC
        swing = rng.choice([-1.0, 1.0])
        for i in range(count):
            if i % 25 == 0:
                swing *= -1.0  # Regime swing

            body_delta = float(rng.normal(swing * atr * 0.12, atr * 0.28))
            open_p = curr_p
            close_p = round(max(min_pip, open_p + body_delta), digits)
            high_p = round(max(open_p, close_p) + max(min_pip, abs(float(rng.normal(0, atr * 0.22)))), digits)
            low_p = round(min(open_p, close_p) - max(min_pip, abs(float(rng.normal(0, atr * 0.22)))), digits)
            vol = float(rng.randint(150, 850))

            candles.append({
                "time": f"T-{count - i}m",
                "open": open_p,
                "high": high_p,
                "low": low_p,
                "close": close_p,
                "volume": vol,
                "atr_14": atr,
            })
            curr_p = close_p

        return candles

    def simulate_pair(
        self,
        symbol: str,
        candles: Optional[List[Dict[str, Any]]] = None,
        base_price: float = 1.0,
    ) -> Dict[str, Any]:
        """Run paper simulation for a single pair using the POC strategy."""
        meta = DERIV_UNIVERSE_CATALOG.get(symbol)
        if not meta:
            return {"symbol": symbol, "error": "Symbol not recognized"}

        spec = meta.spec
        digits = spec.digits

        if not candles or len(candles) < 30:
            candles = self.generate_pair_candles(symbol, base_price=base_price, count=120)

        df = pd.DataFrame(candles)
        pip_unit = spec.tick_size * 10 if spec.digits in (3, 5) else spec.tick_size
        spread_cost = pip_unit * self.spread_pips
        slippage_cost = pip_unit * self.slippage_pips

        balance = self.starting_balance
        trades: List[Dict[str, Any]] = []
        active_trade: Optional[Dict[str, Any]] = None

        warmup = 25
        for i in range(warmup, len(candles)):
            curr_bar = candles[i]
            hist_slice = df.iloc[: i + 1]

            # 1. Manage Active Trade
            if active_trade is not None:
                side = active_trade["side"]
                entry_idx = active_trade["entry_idx"]
                sl = active_trade["stop_loss"]
                tp = active_trade["take_profit"]
                lots = active_trade["lots"]
                duration = i - entry_idx

                hit_tp = False
                hit_sl = False
                exit_price = curr_bar["close"]
                exit_reason = None

                if side == TradeSide.BUY:
                    if curr_bar["high"] >= tp:
                        hit_tp = True
                        exit_price = tp
                        exit_reason = ExitReason.TAKE_PROFIT
                    elif curr_bar["low"] <= sl:
                        hit_sl = True
                        exit_price = sl
                        exit_reason = ExitReason.STOP_LOSS
                else:
                    if curr_bar["low"] <= tp:
                        hit_tp = True
                        exit_price = tp
                        exit_reason = ExitReason.TAKE_PROFIT
                    elif curr_bar["high"] >= sl:
                        hit_sl = True
                        exit_price = sl
                        exit_reason = ExitReason.STOP_LOSS

                # Target duration is 60s (approx 1-2 bars), hard timeout 180s (3-4 bars)
                if not hit_tp and not hit_sl:
                    if duration >= 4:
                        # Allow profitable trades to run, exit stagnant ones
                        unrealized = (
                            (curr_bar["close"] - active_trade["entry_price"])
                            if side == TradeSide.BUY
                            else (active_trade["entry_price"] - curr_bar["close"])
                        )
                        if unrealized <= 0 or duration >= 8:
                            exit_price = curr_bar["close"]
                            exit_reason = ExitReason.TIMEOUT

                if exit_reason is not None:
                    delta = (
                        (exit_price - active_trade["entry_price"])
                        if side == TradeSide.BUY
                        else (active_trade["entry_price"] - exit_price)
                    )
                    ticks = delta / max(spec.tick_size, 1e-9)
                    gross_pnl = ticks * spec.tick_value * lots
                    net_pnl = round(gross_pnl - (lots * self.commission_per_lot), 2)

                    balance += net_pnl
                    active_trade["exit_price"] = exit_price
                    active_trade["profit_loss"] = net_pnl
                    active_trade["exit_reason"] = exit_reason.value
                    active_trade["duration_bars"] = duration
                    active_trade["is_win"] = net_pnl > 0
                    trades.append(active_trade)
                    active_trade = None
                continue

            # 2. Look for new POC Reaction entries
            signal = self.strategy.evaluate(
                symbol=symbol,
                features_df=hist_slice,
                regime=MarketRegime.RANGING,
                spec=spec,
            )

            if signal and signal.side is not None:
                # Sizing to yield meaningful dollar profits ($10 - $40+)
                risk_dollars = max(balance * self.risk_per_trade, 5.0)
                sl_dist = abs(signal.entry_price - signal.stop_loss)
                point_risk = (sl_dist / max(spec.tick_size, 1e-9)) * spec.tick_value
                lots = max(spec.lot_min, round(risk_dollars / max(point_risk, 0.01), 2))
                lots = min(lots, spec.lot_max)

                fill_price = (
                    round(curr_bar["close"] + slippage_cost + (spread_cost / 2), digits)
                    if signal.side == TradeSide.BUY
                    else round(curr_bar["close"] - slippage_cost - (spread_cost / 2), digits)
                )

                active_trade = {
                    "trade_id": f"sim_{symbol}_{len(trades)+1}",
                    "symbol": symbol,
                    "side": signal.side,
                    "lots": lots,
                    "entry_idx": i,
                    "entry_price": fill_price,
                    "stop_loss": signal.stop_loss,
                    "take_profit": signal.take_profit,
                    "poc": signal.metadata.get("poc", curr_bar["close"]),
                    "setup": signal.metadata.get("setup", "POC_REACTION"),
                    "rr": signal.metadata.get("rr", 2.5),
                }

        # Calculate statistics
        total_trades = len(trades)
        winning_trades = [t for t in trades if t["is_win"]]
        losing_trades = [t for t in trades if not t["is_win"]]

        total_profit = round(sum(t["profit_loss"] for t in trades), 2)
        win_rate = round((len(winning_trades) / total_trades * 100.0), 1) if total_trades > 0 else 0.0
        gross_profit = sum(t["profit_loss"] for t in winning_trades)
        gross_loss = abs(sum(t["profit_loss"] for t in losing_trades))
        profit_factor = (
            round(gross_profit / gross_loss, 2)
            if gross_loss > 0
            else (round(gross_profit, 2) if gross_profit > 0 else 1.0)
        )
        avg_trade_profit = round(total_profit / total_trades, 2) if total_trades > 0 else 0.0
        best_trade = max((t["profit_loss"] for t in trades), default=0.0)
        worst_trade = min((t["profit_loss"] for t in trades), default=0.0)

        return {
            "symbol": symbol,
            "description": spec.description,
            "asset_class": spec.asset_class,
            "starting_balance": self.starting_balance,
            "final_balance": round(balance, 2),
            "total_profit": total_profit,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "total_trades": total_trades,
            "winning_count": len(winning_trades),
            "losing_count": len(losing_trades),
            "avg_trade_profit": avg_trade_profit,
            "best_trade_profit": best_trade,
            "worst_trade_profit": worst_trade,
            "trades": trades[-10:],  # Return recent 10 trades for inspection
        }

    def run_multi_pair_simulation(
        self,
        symbols: Optional[List[str]] = None,
        cached_candles: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        live_prices: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Runs paper trading simulation across all candidate pairs,
        and ranks them by total profit to identify the most profitable pair.
        """
        if not symbols:
            symbols = [
                "XAUUSD",
                "Vol_25_1s",
                "Step_Index",
                "Vol_10_1s",
                "Crash_500",
                "EURUSD",
                "USDJPY",
                "GBPUSD",
                "Boom_1000",
                "Vol_75",
            ]

        results = []
        for sym in symbols:
            candles = cached_candles.get(sym) if cached_candles else None
            price = live_prices.get(sym, 100.0) if live_prices else 100.0
            res = self.simulate_pair(sym, candles=candles, base_price=price)
            if "error" not in res:
                results.append(res)

        # Rank pairs by Total Profit (descending)
        results.sort(key=lambda x: x["total_profit"], reverse=True)

        for rank_idx, r in enumerate(results, start=1):
            r["rank"] = rank_idx

        top_pair = results[0]["symbol"] if results else "None"
        max_profit = results[0]["total_profit"] if results else 0.0

        return {
            "top_profitable_symbol": top_pair,
            "top_profit": max_profit,
            "total_pairs_simulated": len(results),
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            "rankings": results,
        }
