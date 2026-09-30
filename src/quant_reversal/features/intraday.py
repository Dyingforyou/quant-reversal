from datetime import time
import pandas as pd
def intraday_snapshots(bars:pd.DataFrame,prev_close:float,ma5_ref:float,auction_price:float,history_open5_amount:pd.Series)->pd.DataFrame:
    b=bars.sort_values("minute").copy(); b=b[pd.to_datetime(b.minute.astype(str),format="%H:%M").dt.time<=time(10,0)]
    b["index_minute"]=range(len(b)); red=b.close>=prev_close; reclaim=b.close>=ma5_ref
    first_red=int(b.loc[red,"index_minute"].min()) if red.any() else None; first_ma=int(b.loc[reclaim,"index_minute"].min()) if reclaim.any() else None
    b["minutes_to_red"]=first_red; b["minutes_to_reclaim_ma5"]=first_ma
    b["reversal_strength"]=b.close/auction_price-1; b["intraday_low_vs_ma5"]=b.low.cummin()/ma5_ref-1; b["intraday_high_vs_open"]=b.high.cummax()/auction_price-1
    below=b.close<ma5_ref; b["rebreak_ma5_count"]=(below & ~below.shift(1,fill_value=True)).cumsum()
    hist=history_open5_amount.dropna(); base=hist.median() if len(hist) else float("nan")
    # The opening five-minute total only becomes available at 09:35. Earlier
    # snapshots must not see later bars from the same frame.
    opening=b[b.minute.astype(str).between("09:31","09:35")]
    complete=set(opening.minute.astype(str))=={"09:31","09:32","09:33","09:34","09:35"}
    ratio=opening.amount.sum()/base if complete and base and pd.notna(base) else float("nan")
    b["open5m_volume_ratio20"]=b.minute.astype(str).map(lambda minute: ratio if minute>="09:35" else float("nan"))
    return b
