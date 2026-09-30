"""Market sentiment features observable from completed daily bars."""
import numpy as np
import pandas as pd


def add_market_sentiment(df: pd.DataFrame) -> pd.DataFrame:
    out = df.sort_values(["trade_date", "symbol"]).copy()
    day = pd.to_datetime(out.trade_date).dt.date
    out["market_highest_board"] = out.groupby(day).limit_up_streak.transform("max").astype(int)
    out["market_limit_down_count"] = out.groupby(day)["close"].transform(
        lambda values: 0
    ).astype(int)
    down = (out.close <= out.limit_down_price + 0.001).groupby(day).sum().to_dict()
    touched = out.is_touched_limit_up.groupby(day).sum()
    closed = out.is_closed_limit_up.groupby(day).sum()
    bust = ((touched - closed) / touched.replace(0, np.nan)).fillna(0).to_dict()
    board_return = out[out.prev_streak_height > 0].groupby(day).break_return.mean().to_dict()
    out["market_limit_down_count"] = day.map(down).fillna(0).astype(int)
    out["market_bust_rate"] = day.map(bust).fillna(0.0).astype(float)
    out["market_board_stock_avg_return"] = day.map(board_return).fillna(0.0).astype(float)

    dates = sorted(day.unique())
    advancement = {}
    leader_return = {}
    for i, current in enumerate(dates):
        current_rows = out[day == current]
        if i:
            previous = dates[i - 1]
            previous_rows = out[day == previous]
            prior_closed = set(previous_rows.loc[previous_rows.is_closed_limit_up, "symbol"].astype(str))
            promoted = current_rows[current_rows.symbol.astype(str).isin(prior_closed)].is_closed_limit_up.sum()
            advancement[current] = float(promoted / len(prior_closed)) if prior_closed else 0.0
            highest = int(previous_rows.limit_up_streak.max())
            leaders = set(previous_rows.loc[previous_rows.limit_up_streak == highest, "symbol"].astype(str))
            returns = current_rows[current_rows.symbol.astype(str).isin(leaders)].break_return
            leader_return[current] = float(returns.mean()) if len(returns) else 0.0
        else:
            advancement[current] = leader_return[current] = 0.0
    out["market_advancement_rate"] = day.map(advancement).astype(float)
    out["previous_leader_today_return"] = day.map(leader_return).astype(float)
    out["high_stock_next_day_premium"] = out["previous_leader_today_return"]
    return out


def sentiment_score(row: pd.Series) -> float:
    score = 0.5
    score += 0.25 * float(row.get("market_advancement_rate", 0.0))
    score += 0.15 * max(-1.0, min(1.0, float(row.get("previous_leader_today_return", 0.0)) / 0.1))
    score -= 0.25 * float(row.get("market_bust_rate", 0.0))
    score -= min(0.25, float(row.get("market_limit_down_count", 0)) / 80)
    return float(max(0.0, min(1.0, score)))
