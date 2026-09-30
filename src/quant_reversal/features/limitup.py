import pandas as pd
def add_limit_up_features(df: pd.DataFrame, tolerance: float = 0.001) -> pd.DataFrame:
    out=df.copy(); p=out.limit_up_price
    out["is_one_price_limit_up"]=out.low >= p-tolerance
    out["is_touched_limit_up"]=out.high >= p-tolerance
    out["is_closed_limit_up"]=out.close >= p-tolerance
    return out

