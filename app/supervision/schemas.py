"""
Pydantic Schemas and Typed Contracts for Institutional LLM Supervision.
Enforces rigorous validation bounds to prevent model hallucination in risk execution.
"""

from __future__ import annotations

from typing import List, Dict, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class MacroSupervisoryDirective(BaseModel):
    """
    Supervisory macro directive issued by the LLM Supervisory Agent.
    Strictly validated: risk multipliers cannot exceed hard limits.
    """
    directive_id: str
    timestamp: datetime
    regime_assessment: str = Field(
        ...,
        description="Assessed macro regime, e.g., CALM_TRENDING, VOLATILITY_EXPANSION, NEWS_SHOCK, RANGEBOUND"
    )
    risk_multiplier_cap: float = Field(
        default=1.0,
        description="Enforced ceiling on strategy risk multiplier [0.0, 1.5]."
    )
    forbidden_symbols: List[str] = Field(
        default_factory=list,
        description="Symbols strictly prohibited from opening new exposure."
    )
    recommended_focus_symbols: List[str] = Field(
        default_factory=list,
        description="High-conviction symbols recommended for allocation."
    )
    macro_rationale: str = Field(
        ...,
        min_length=10,
        description="Structured reasoning explaining the directive without speculation."
    )
    confidence: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Supervisor confidence level in this assessment."
    )

    @field_validator("risk_multiplier_cap", mode="before")
    @classmethod
    def validate_risk_cap(cls, v: Any) -> float:
        val = float(v)
        if val > 1.5:
            return 1.5
        if val < 0.0:
            return 0.0
        return round(val, 2)


class PostMortemAttributionReport(BaseModel):
    """
    Institutional post-mortem audit of an individual trade or sequence of trades.
    Identifies root causes (slippage, adverse selection, regime mismatch, or standard variance).
    """
    trade_id: str
    symbol: str
    pnl: float
    root_cause_category: Literal[
        "SLIPPAGE_OR_LATENCY_DRAG",
        "REGIME_MISMATCH",
        "PREMATURE_STOP_OUT",
        "ALPHA_DECAY",
        "NORMAL_STATISTICAL_VARIANCE",
        "VOLATILITY_EXPANSION_SPIKE"
    ]
    execution_drag_identified: bool = False
    model_confidence_was_overfit: bool = False
    suggested_action: str = Field(..., min_length=5)
    supervisor_notes: str = Field(..., min_length=10)


class DeskExecutiveBriefing(BaseModel):
    """
    Daily executive briefing synthesizing live tournament alpha, risk status,
    and broker state into an institutional trading desk report.
    """
    briefing_id: str
    timestamp: datetime
    overall_posture: Literal["AGGRESSIVE_ALPHA", "BALANCED", "DEFENSIVE", "HALTED_CIRCUIT_BREAKER"]
    active_circuit_breaker: bool = False
    portfolio_equity: float
    portfolio_drawdown_pct: float
    top_performing_strategy: str
    capital_allocation_summary: Dict[str, float] = Field(default_factory=dict)
    key_risks_monitored: List[str] = Field(default_factory=list)
    executive_summary: str = Field(..., min_length=15)
