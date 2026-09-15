"""
Application settings and environment configuration.
Loads parameters from .env and enforces strict typing and validation.
"""

from functools import lru_cache
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="AITradingEngine", alias="APP_NAME")
    trading_mode: Literal["paper", "demo", "live"] = Field(
        default="paper", alias="TRADING_MODE"
    )
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Database
    database_url: str = Field(
        default="sqlite:///data/trading_ai.db", alias="DATABASE_URL"
    )

    # cTrader Credentials
    ctrader_client_id: str = Field(default="", alias="CTRADER_CLIENT_ID")
    ctrader_client_secret: str = Field(default="", alias="CTRADER_CLIENT_SECRET")
    ctrader_access_token: str = Field(default="", alias="CTRADER_ACCESS_TOKEN")
    ctrader_refresh_token: str = Field(default="", alias="CTRADER_REFRESH_TOKEN")
    ctrader_account_id: str = Field(default="", alias="CTRADER_ACCOUNT_ID")
    ctrader_environment: Literal["demo", "live"] = Field(
        default="demo", alias="CTRADER_ENVIRONMENT"
    )
    ctrader_host_demo: str = Field(
        default="demo.ctraderapi.com", alias="CTRADER_HOST_DEMO"
    )
    ctrader_host_live: str = Field(
        default="live.ctraderapi.com", alias="CTRADER_HOST_LIVE"
    )
    ctrader_port: int = Field(default=5035, alias="CTRADER_PORT")

    # Risk Engine
    risk_per_trade: float = Field(default=0.005, alias="RISK_PER_TRADE")  # 0.5%
    max_daily_loss: float = Field(default=0.02, alias="MAX_DAILY_LOSS")   # 2.0%
    max_drawdown: float = Field(default=0.10, alias="MAX_DRAWDOWN")       # 10.0%
    max_open_positions: int = Field(default=3, alias="MAX_OPEN_POSITIONS")
    max_correlated_exposure: float = Field(
        default=0.70, alias="MAX_CORRELATED_EXPOSURE"
    )
    min_risk_reward: float = Field(default=1.5, alias="MIN_RISK_REWARD")
    max_spread_pips: float = Field(default=3.0, alias="MAX_SPREAD_PIPS")

    # Scanner & Timeframes
    scan_interval_seconds: float = Field(
        default=1.0, alias="SCAN_INTERVAL_SECONDS"
    )
    max_markets: int = Field(default=50, alias="MAX_MARKETS")
    default_timeframe: str = Field(default="1m", alias="DEFAULT_TIMEFRAME")
    higher_timeframe: str = Field(default="5m", alias="HIGHER_TIMEFRAME")
    macro_timeframe: str = Field(default="15m", alias="MACRO_TIMEFRAME")

    # Scalping & Stagnation
    target_duration_seconds: int = Field(
        default=60, alias="TARGET_DURATION_SECONDS"
    )
    soft_timeout_seconds: int = Field(
        default=90, alias="SOFT_TIMEOUT_SECONDS"
    )
    hard_timeout_seconds: int = Field(
        default=180, alias="HARD_TIMEOUT_SECONDS"
    )
    stagnation_candle_count: int = Field(
        default=6, alias="STAGNATION_CANDLE_COUNT"
    )

    # AI & ML Filters
    min_direction_probability: float = Field(
        default=0.75, alias="MIN_DIRECTION_PROBABILITY"
    )
    min_trade_quality: float = Field(default=0.70, alias="MIN_TRADE_QUALITY")
    max_whipsaw_probability: float = Field(
        default=0.25, alias="MAX_WHIPSAW_PROBABILITY"
    )

    # Paper Broker Defaults
    paper_starting_balance: float = Field(
        default=10000.0, alias="PAPER_STARTING_BALANCE"
    )
    paper_leverage: float = Field(default=100.0, alias="PAPER_LEVERAGE")
    paper_spread_pips: float = Field(default=0.8, alias="PAPER_SPREAD_PIPS")
    paper_slippage_pips: float = Field(default=0.2, alias="PAPER_SLIPPAGE_PIPS")
    paper_commission_per_lot: float = Field(
        default=3.50, alias="PAPER_COMMISSION_PER_LOT"
    )


@lru_cache()
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
