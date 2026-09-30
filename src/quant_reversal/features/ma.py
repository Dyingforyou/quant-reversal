import pandas as pd
def add_ma_reference(df: pd.DataFrame, lookback: int = 5) -> pd.DataFrame:
    out=df.sort_values(["symbol","trade_date"]).copy()
    out["ma5_ref"]=out.groupby("symbol").close.transform(lambda s:s.shift(1).rolling(lookback,min_periods=lookback).mean())
    return out
def score_ma5(distance: float) -> float:
    if pd.isna(distance): return 0
    if -.005<=distance<=.01:return 15
    if -.01<=distance<=.02:return 12
    if -.02<=distance<=.03:return 8
    return 0

