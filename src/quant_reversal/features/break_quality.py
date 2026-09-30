"""First-break quality and turnover/chip proxies supported by daily bars."""
from __future__ import annotations

import numpy as np
import pandas as pd


def _quality(row: pd.Series) -> str:
    if not bool(row.get("is_first_break", False)):
        return "非断板日"
    ret = float(row["break_return"])
    touched = bool(row.get("is_touched_limit_up", False))
    at_down = float(row["close"]) <= float(row["limit_down_price"]) + 0.001
    if touched and at_down:
        return "天地板"
    if at_down:
        return "跌停"
    if ret <= -0.07:
        return "大阴"
    if ret <= -0.03:
        return "中阴"
    upper = (float(row["high"]) - max(float(row["open"]), float(row["close"]))) / max(
        np.finfo(float).eps, float(row["high"]) - float(row["low"])
    )
    if upper >= 0.5:
        return "长上影"
    if touched and ret >= 0:
        return "炸板收红"
    if touched:
        return "炸板小阴"
    return "收红" if ret >= 0 else "小阴"


def add_break_quality(df: pd.DataFrame, lookback: int = 20) -> pd.DataFrame:
    out = df.sort_values(["symbol", "trade_date"]).copy()
    out["break_quality"] = out.apply(_quality, axis=1)
    out["break_max_drawdown"] = out.low / out.high.replace(0, np.nan) - 1
    out["tail_support"] = np.nan  # Requires break-day late-session minute/tick history.
    avg_amount = out.groupby("symbol").amount.transform(
        lambda values: values.shift(1).rolling(lookback, min_periods=lookback).mean()
    )
    prior_max = out.groupby("symbol").amount.transform(lambda values: values.shift(1).cummax())
    out["amount_ratio20_mean"] = out.amount / avg_amount
    out["is_historical_record_amount"] = out.amount >= prior_max
    out["first_limit_time"] = None
    out["last_limit_time"] = None
    out["limit_break_count"] = np.nan
    out["sealed_duration_minutes"] = np.nan
    out["sealed_order_amount"] = np.nan
    out["sealed_order_to_float_cap"] = np.nan
    out["board_type"] = np.select(
        [out.is_one_price_limit_up, out.is_closed_limit_up & (out.open >= out.limit_up_price - 0.001)],
        ["一字板", "T字板"],
        default=np.where(out.is_closed_limit_up, "换手板", "非涨停"),
    )
    return out
