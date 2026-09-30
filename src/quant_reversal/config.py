"""Validated YAML configuration."""
from __future__ import annotations

from pathlib import Path
from typing import Literal
import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

class ProjectConfig(StrictModel):
    timezone: str = "Asia/Shanghai"
    output_dir: Path = Path("data/outputs")
    data_dir: Path = Path("data/fixtures")
class CandidateConfig(StrictModel):
    research_min_board: int = Field(2, ge=2); research_max_board: int = Field(10, ge=2)
    require_first_break: bool = True
    signal_delay_days: int = 1; exclude_suspended: bool = True
    hard_filter_ma5: bool = False; hard_filter_auction: bool = False
    @model_validator(mode="after")
    def valid_range(self):
        if self.research_min_board > self.research_max_board: raise ValueError("research_min_board must be <= research_max_board")
        return self
class LimitupConfig(StrictModel): price_tolerance: float = Field(0.001, ge=0)
class MA5Config(StrictModel):
    lookback: int = Field(5, ge=2); min_distance: float = -0.02; max_distance: float = 0.03
    reference: Literal["previous_close_ma"] = "previous_close_ma"
class AuctionConfig(StrictModel):
    lookback: int = Field(20, ge=1); baseline: Literal["median"] = "median"
    volume_ratio_min: float = 1.5; amount_ratio_min: float = 1.5; gap_min: float = -0.06; gap_max: float = 0.03
class IntradayConfig(StrictModel):
    confirm_window_minutes: int = 30; max_entry_time: str = "10:00"
    require_reclaim_prev_close: bool = False; require_reclaim_ma5: bool = True
    open5m_volume_ratio_min: float = 1.2; max_rebreak_ma5_count: int = 1
class SectorConfig(StrictModel):
    type_priority: list[str] = ["concept", "industry"]; min_members: int = 3; lookback_days: int = 20
class ScoreConfig(StrictModel):
    sector_weight: float = 20; stock_weight: float = 20; break_weight: float = 15
    ma5_weight: float = 15; auction_weight: float = 20; market_weight: float = 10
    grade_a: float = 80; grade_b: float = 70; watch: float = 60
class ModelWeights(StrictModel):
    board_range: tuple[int, int] | None = None; min_board: int | None = None
    sector_weight: float; stock_weight: float; break_weight: float; ma5_weight: float
    auction_weight: float; height_rank_weight: float; turnover_weight: float; sentiment_weight: float
    @model_validator(mode="after")
    def valid_weights(self):
        total=sum([self.sector_weight,self.stock_weight,self.break_weight,self.ma5_weight,self.auction_weight,self.height_rank_weight,self.turnover_weight,self.sentiment_weight])
        if abs(total-100)>0.001: raise ValueError(f"sub-model weights must sum to 100, got {total}")
        return self
class StrategyModelsConfig(StrictModel):
    low_height: ModelWeights
    mid_height: ModelWeights
    high_leader: ModelWeights
class EntryConfig(StrictModel): mode: Literal["auction", "intraday_confirmed"] = "intraday_confirmed"; slippage_bps: float = 10
class ExitConfig(StrictModel):
    base_mode: Literal["next_day_1000", "stop", "take_profit", "max_holding"] = "next_day_1000"
    fixed_stop_pct: float = -0.05; take_profit_pct: float = 0.08; max_holding_days: int = 3
class CostsConfig(StrictModel): commission_bps: float = 3; min_commission: float = 5; sell_tax_bps: float = 10
class BacktestConfig(StrictModel):
    initial_cash: float = 1_000_000; max_positions: int = 5; position_size_pct: float = 0.2
    reject_same_bar_fill: bool = True; enforce_t1: bool = True; lot_size: int = 100
class AppConfig(StrictModel):
    project: ProjectConfig; candidate: CandidateConfig; limitup: LimitupConfig = LimitupConfig()
    ma5: MA5Config; auction: AuctionConfig; intraday: IntradayConfig; sector: SectorConfig
    score: ScoreConfig; models: StrategyModelsConfig; entry: EntryConfig; exit: ExitConfig; costs: CostsConfig; backtest: BacktestConfig

def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for key, value in override.items():
        out[key] = _deep_merge(out.get(key, {}), value) if isinstance(value, dict) and isinstance(out.get(key), dict) else value
    return out

def load_config(path: str | Path) -> AppConfig:
    """Load a YAML config, resolving an optional sibling include."""
    path = Path(path).resolve()
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    include = raw.pop("include", None)
    if include:
        base = yaml.safe_load((path.parent / include).read_text(encoding="utf-8")) or {}
        raw = _deep_merge(base, raw)
    cfg = AppConfig.model_validate(raw)
    root = path.parent.parent
    if not cfg.project.data_dir.is_absolute(): cfg.project.data_dir = (root / cfg.project.data_dir).resolve()
    if not cfg.project.output_dir.is_absolute(): cfg.project.output_dir = (root / cfg.project.output_dir).resolve()
    return cfg
