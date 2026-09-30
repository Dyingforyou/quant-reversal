import pandas as pd
def add_streak_features(df: pd.DataFrame) -> pd.DataFrame:
    out=df.sort_values(["symbol","trade_date"]).copy(); streak=[]; prev=[]; ends=[]
    for _,g in out.groupby("symbol",sort=False):
        run=0; end=None
        for row in g.itertuples():
            before=run
            if bool(row.is_trading) and bool(row.is_closed_limit_up): run+=1; end=row.trade_date
            elif bool(row.is_trading): run=0
            streak.append(run); prev.append(before); ends.append(end if run==0 else row.trade_date)
    out["limit_up_streak"]=streak; out["prev_streak_height"]=prev; out["streak_end_date"]=ends
    return out
