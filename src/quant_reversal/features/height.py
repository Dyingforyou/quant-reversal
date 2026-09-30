"""Board-height context and sub-strategy routing without future data."""
from __future__ import annotations

import pandas as pd


def strategy_for_height(board_count: int) -> tuple[str, str]:
    if board_count <= 3:
        return "LowHeightReversal", "低位反包"
    if board_count <= 5:
        return "MidHeightReversal", "中位反包"
    return "HighLeaderReversal", "高标反包"


def add_height_context(df: pd.DataFrame) -> pd.DataFrame:
    """Attach cycle and prior-market height fields to each daily row."""
    out = df.sort_values(["symbol", "trade_date"]).reset_index(drop=True).copy()
    cycle_start = [None] * len(out)
    cycle_high = [0] * len(out)
    break_count = [0] * len(out)
    one_price_count = [0] * len(out)
    turnover_count = [0] * len(out)
    closed = out.is_closed_limit_up.astype(bool).to_numpy()
    streak = out.limit_up_streak.astype(int).to_numpy()
    previous_streak = out.prev_streak_height.astype(int).to_numpy()
    one_price_flag = out.is_one_price_limit_up.astype(bool).to_numpy()
    trade_dates = out.trade_date.to_numpy()

    for indexes in out.groupby("symbol", sort=False).indices.values():
        start = None
        high = one_price = turnover = 0
        broken = False
        for idx in indexes:
            if closed[idx]:
                if streak[idx] == 1:
                    start, high, one_price, turnover, broken = trade_dates[idx], 0, 0, 0, False
                high = max(high, streak[idx])
                one_price += int(one_price_flag[idx])
                turnover += int(not one_price_flag[idx])
            elif previous_streak[idx] > 0:
                broken = True
            elif broken:
                start, high, one_price, turnover, broken = None, 0, 0, 0, False
            cycle_start[idx] = start
            cycle_high[idx] = high
            break_count[idx] = int(broken)
            one_price_count[idx] = one_price
            turnover_count[idx] = turnover
    out["cycle_start_date"] = pd.Series(cycle_start, dtype="object")
    out["cycle_board_high"] = cycle_high
    out["break_count_in_cycle"] = break_count
    out["one_price_boards_in_cycle"] = one_price_count
    out["turnover_boards_in_cycle"] = turnover_count

    dates = sorted(pd.to_datetime(out.trade_date).dt.date.unique())
    current_max = out.groupby(pd.to_datetime(out.trade_date).dt.date).limit_up_streak.max().to_dict()
    previous_max = {day: int(current_max.get(dates[i - 1], 0)) if i else 0 for i, day in enumerate(dates)}
    day_values = pd.to_datetime(out.trade_date).dt.date
    out["prev_market_highest_board"] = day_values.map(previous_max).fillna(0).astype(int)
    out["is_market_highest"] = (
        out["prev_streak_height"].astype(int) == out["prev_market_highest_board"]
    ) & (out["prev_streak_height"].astype(int) > 0)

    board_count = out["prev_streak_height"].where(out["prev_streak_height"] > 0, out["limit_up_streak"])
    out["board_count"] = board_count.astype(int)
    out["height_rank"] = out.groupby("trade_date")["board_count"].rank(method="dense", ascending=False).astype(int)
    out["same_height_count"] = out.groupby(["trade_date", "board_count"])["symbol"].transform("count").astype(int)
    routed = out.board_count.map(lambda value: strategy_for_height(int(value)))
    out["sub_strategy"] = routed.map(lambda value: value[0])
    out["height_group"] = routed.map(lambda value: value[1])
    return out


def height_score(board_count: int, height_rank: int, is_market_highest: bool) -> float:
    rank_part = 1.0 if is_market_highest else 0.75 if height_rank == 2 else 0.5 if height_rank <= 4 else 0.25
    height_part = min(1.0, max(0.0, board_count / 8))
    return float(0.65 * rank_part + 0.35 * height_part)
