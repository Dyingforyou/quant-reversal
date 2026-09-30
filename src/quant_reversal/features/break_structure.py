import numpy as np
import pandas as pd
def add_break_features(df: pd.DataFrame, lookback: int = 20) -> pd.DataFrame:
    out=df.sort_values(["symbol","trade_date"]).copy()
    out["is_first_break"]=(out.is_trading.astype(bool)&~out.is_closed_limit_up.astype(bool)&(out.prev_streak_height>0))
    out["break_gap"]=out.open/out.prev_close-1; out["break_return"]=out.close/out.prev_close-1
    out["break_intraday_range"]=(out.high-out.low)/out.prev_close
    out["break_close_position"]=(out.close-out.low)/(out.high-out.low).clip(lower=np.finfo(float).eps)
    baseline=out.groupby("symbol").amount.transform(lambda s:s.shift(1).rolling(lookback,min_periods=lookback).median())
    out["break_amount_ratio20"]=out.amount/baseline
    return out
def score_break(is_first_break: bool, close_position: float, amount_ratio: float, break_return: float) -> float:
    if not is_first_break:return 0.0
    score=8+(3 if close_position>=.6 else 1.5 if close_position>=.3 else 0)
    score+=2 if .8<=amount_ratio<=2.5 else 0; score+=2 if break_return>=-.07 else 0
    return min(15.0,score)

