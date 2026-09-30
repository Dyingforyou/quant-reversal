"""Future labels. Strategy modules never import this module."""
import numpy as np
import pandas as pd
def build_labels(entry_price:float,future_daily:pd.DataFrame,future_minutes:pd.DataFrame)->dict:
    d=future_daily.sort_values("trade_date"); first=d.iloc[0] if len(d) else None
    minute1000=future_minutes[future_minutes.minute.astype(str)=="10:00"]
    def ret(v):return float(v/entry_price-1) if v is not None and pd.notna(v) else np.nan
    out={"next_day_open_return":ret(first.open if first is not None else None),"next_day_1000_return":ret(minute1000.iloc[0].close if len(minute1000) else None),"next_day_close_return":ret(first.close if first is not None else None)}
    for n in [1,2,3]:
        part=d.iloc[:n]; out[f"future_{n}d_max_return"]=ret(part.high.max()) if len(part) else np.nan; out[f"future_{n}d_min_return"]=ret(part.low.min()) if len(part) else np.nan
    out.update({"mfe_1d":out["future_1d_max_return"],"mae_1d":out["future_1d_min_return"],"mfe_3d":out["future_3d_max_return"],"mae_3d":out["future_3d_min_return"]}); return out

