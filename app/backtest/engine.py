"""
Event-Driven Backtesting Engine.
Zero look-ahead bias, realistic spreads, slippage, and deterministic risk management.
Section 42 and 79 of project.md.
"""

from typing import List, Dict, Any, Optional
import pandas as pd
from loguru import logger

from app.broker.models import (
    Candle,
    SymbolSpecification,
    TradeSide,
    ExitReason,
    AccountInfo,
    Tick,
)
from app.features.feature_pipeline import FeaturePipeline
from app.strategies.router import StrategyRouter
from app.ai.inference import AIInferenceEngine
from app.risk.manager import RiskEngine
from app.backtest.metrics import calculate_backtest_metrics


class BacktestEngine:
    """
    Simulates historical trading execution step-by-step.
    """

    def __init__(
        self,
        starting_balance: float = 10000.0,
        spread_pips: float = 0.8,
        slippage_pips: float = 0.2,
        commission_per_lot: float = 3.50,
        max_duration_bars: int = 15,
    ):
        self.starting_balance = starting_balance
        self.balance = starting_balance
        self.equity = starting_balance
        self.spread_pips = spread_pips
        self.slippage_pips = slippage_pips
        self.commission_per_lot = commission_per_lot
        self.max_duration_bars = max_duration_bars

        self.strategy_router = StrategyRouter()
        self.ai_engine = AIInferenceEngine()
        self.risk_engine = RiskEngine()

    def run(
        self,
        candles: List[Candle],
        spec: SymbolSpecification,
        warmup_bars: int = 50,
    ) -> Dict[str, Any]:
        """
        Run backtest across chronological candles.
        """
        if len(candles) < warmup_bars + 20:
            return {"error": "Insufficient candle count for backtest"}

        logger.info(f"Running backtest on {spec.symbol} across {len(candles)} candles...")
        df_all = FeaturePipeline.candles_to_dataframe(candles)

        # Precompute features historically
        feat_df = FeaturePipeline.compute_all_features(df_all)

        trades: List[Dict[str, Any]] = []
        active_trade: Optional[Dict[str, Any]] = None

        pip_unit = spec.tick_size * 10 if spec.digits in (3, 5) else spec.tick_size
        spread_cost = pip_unit * self.spread_pips
        slippage_cost = pip_unit * self.slippage_pips

        for i in range(warmup_bars, len(candles)):
            curr_candle = candles[i]
            # Slices up to i strictly prevent any future lookahead
            hist_features = feat_df.iloc[: i + 1]

            # 1. Manage Active Trade
            if active_trade is not None:
                side = active_trade["side"]
                entry_idx = active_trade["entry_idx"]
                sl = active_trade["stop_loss"]
                tp = active_trade["take_profit"]
                lots = active_trade["volume_lots"]
                duration = i - entry_idx

                hit_tp = False
                hit_sl = False
                exit_price = curr_candle.close
                exit_reason = None

                if side == TradeSide.BUY:
                    if curr_candle.high >= tp:
                        hit_tp = True
                        exit_price = tp
                        exit_reason = ExitReason.TAKE_PROFIT
                    elif curr_candle.low <= sl:
                        hit_sl = True
                        exit_price = sl
                        exit_reason = ExitReason.STOP_LOSS
                else:
                    if curr_candle.low <= tp:
                        hit_tp = True
                        exit_price = tp
                        exit_reason = ExitReason.TAKE_PROFIT
                    elif curr_candle.high >= sl:
                        hit_sl = True
                        exit_price = sl
                        exit_reason = ExitReason.STOP_LOSS

                # Timeout check
                if not hit_tp and not hit_sl and duration >= self.max_duration_bars:
                    exit_price = curr_candle.close
                    exit_reason = ExitReason.TIMEOUT

                if exit_reason is not None:
                    # Calculate PnL
                    delta = (
                        (exit_price - active_trade["entry_price"])
                        if side == TradeSide.BUY
                        else (active_trade["entry_price"] - exit_price)
                    )
                    ticks = delta / max(spec.tick_size, 1e-9)
                    pnl = (ticks * spec.tick_value * lots) - (lots * self.commission_per_lot * 2.0)

                    self.balance += pnl
                    active_trade["exit_price"] = exit_price
                    active_trade["profit_loss"] = round(pnl, 2)
                    active_trade["exit_reason"] = exit_reason.value
                    active_trade["duration_bars"] = duration
                    trades.append(active_trade)
                    active_trade = None
                continue

            # 2. Look for new entries if no trade is active
            from app.ai.regime.detector import RegimeDetector
            regime, regime_conf = RegimeDetector.detect_regime(hist_features)

            candidates = self.strategy_router.route_and_evaluate(
                symbol=spec.symbol,
                features_df=hist_features,
                regime=regime,
                spec=spec,
            )

            if not candidates:
                continue

            best_candidate = candidates[0]

            # AI Inference
            ai_decision = self.ai_engine.evaluate_market_and_signal(
                symbol=spec.symbol,
                features_df=hist_features,
                candidate_signal=best_candidate,
                spec=spec,
            )

            # Account snapshot for risk
            account = AccountInfo(
                account_id="BACKTEST",
                broker="Backtest",
                balance=self.balance,
                equity=self.balance,
                free_margin=self.balance * 0.9,
            )
            sim_tick = Tick(
                symbol=spec.symbol,
                bid=curr_candle.close - (spread_cost / 2),
                ask=curr_candle.close + (spread_cost / 2),
            )

            # Risk Engine evaluation
            risk_decision = self.risk_engine.evaluate_trade(
                signal=best_candidate,
                ai_decision=ai_decision,
                account=account,
                spec=spec,
                current_tick=sim_tick,
                open_positions=[],
            )

            if risk_decision.approved and risk_decision.side is not None:
                # Enter trade with slippage & spread
                fill_price = (
                    curr_candle.close + slippage_cost + (spread_cost / 2)
                    if risk_decision.side == TradeSide.BUY
                    else curr_candle.close - slippage_cost - (spread_cost / 2)
                )

                active_trade = {
                    "symbol": spec.symbol,
                    "side": risk_decision.side,
                    "entry_idx": i,
                    "entry_price": fill_price,
                    "stop_loss": risk_decision.stop_loss,
                    "take_profit": risk_decision.take_profit,
                    "volume_lots": risk_decision.volume_lots,
                    "strategy": best_candidate.strategy,
                    "ai_quality": ai_decision.trade_quality,
                    "regime": regime.value,
                }

        # Compute summary metrics
        metrics = calculate_backtest_metrics(trades, starting_balance=self.starting_balance)
        logger.info(
            f"Backtest complete: {metrics['total_trades']} trades, "
            f"Win Rate: {metrics['win_rate']*100:.1f}%, Profit Factor: {metrics['profit_factor']}, "
            f"Net PnL: ${metrics['net_profit']:+.2f} ({metrics['return_pct']:+.1f}%)"
        )
        return {"metrics": metrics, "trades": trades}
