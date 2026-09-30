"""Normalization helpers for provider adapters."""
import pandas as pd
def normalize_dates(frame: pd.DataFrame, columns=("trade_date",)) -> pd.DataFrame:
    out=frame.copy()
    for col in columns:
        if col in out: out[col]=pd.to_datetime(out[col]).dt.date
    return out

