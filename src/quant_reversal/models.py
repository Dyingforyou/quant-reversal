"""Domain models; labels intentionally live outside this module."""
from datetime import date, datetime
from enum import StrEnum
from typing import Any, Literal
from pydantic import BaseModel, Field

class FeatureSnapshot(BaseModel):
    signal_date: date; symbol: str; available_at: datetime | None = None
    values: dict[str, Any] = Field(default_factory=dict)
class Candidate(BaseModel):
    signal_date: date; symbol: str; best_sector_id: str | None = None
    prev_streak_height: int; is_first_break: bool; ma5_ref: float; ma5_distance_auction: float
    board_count: int = 0; height_group: str = ""; height_rank: int = 0
    is_market_highest: bool = False; same_height_count: int = 0
    sub_strategy: str = "LowHeightReversal"; model_route_reason: str = ""
    sector_score: float = 0; stock_score: float = 0; break_score: float = 0; ma5_score: float = 0
    auction_score: float = 0; market_score: float = 0; height_score: float = 0
    turnover_score: float = 0; sentiment_score: float = 0; total_score: float = 0; grade: str = "REJECT"
    reasons: list[str] = Field(default_factory=list); raw_features: dict[str, Any] = Field(default_factory=dict)
class SignalEvent(BaseModel):
    timestamp: datetime; symbol: str; type: Literal["ENTRY_TRIGGER", "EXIT_TRIGGER"]; available_at: datetime
class Side(StrEnum): BUY = "BUY"; SELL = "SELL"
class Order(BaseModel):
    symbol: str; side: Side; quantity: int; created_at: datetime; earliest_fill_at: datetime; reason: str = ""
class Fill(BaseModel):
    symbol: str; side: Side; quantity: int; price: float; timestamp: datetime; commission: float = 0; tax: float = 0
class Position(BaseModel): symbol: str; quantity: int; entry_price: float; entry_date: date; entry_cost: float = 0
class Trade(BaseModel):
    symbol: str; entry_time: datetime; entry_price: float; exit_time: datetime; exit_price: float
    quantity: int; costs: float; return_pct: float; holding_days: int; score_grade: str = ""
class BacktestResult(BaseModel):
    trades: list[Trade] = Field(default_factory=list); metrics: dict[str, Any] = Field(default_factory=dict)
    no_fill_count: int = 0; locked_limit_down_exit_count: int = 0
