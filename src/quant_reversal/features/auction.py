import numpy as np
import pandas as pd
def add_auction_features(auction: pd.DataFrame, daily: pd.DataFrame, lookback: int=20) -> pd.DataFrame:
    a=auction.sort_values(["symbol","trade_date"]).copy()
    for col in ["auction_volume","auction_amount"]:
        base=a.groupby("symbol")[col].transform(lambda s:s.shift(1).rolling(lookback,min_periods=lookback).median())
        a[f"{col}_ratio20"]=a[col]/base
    prior=daily[["trade_date","symbol","close","amount"]].copy()
    prior["trade_date"]=pd.to_datetime(prior.trade_date)
    a["trade_date"]=pd.to_datetime(a.trade_date)
    parts=[]
    for symbol,current in a.groupby("symbol",sort=False):
        history=prior[prior.symbol==symbol].drop(columns="symbol").sort_values("trade_date")
        joined=pd.merge_asof(current.sort_values("trade_date"),history,on="trade_date",direction="backward",allow_exact_matches=False)
        joined["symbol"]=symbol;parts.append(joined)
    a=pd.concat(parts,ignore_index=True).rename(columns={"close":"prev_close_known","amount":"prev_day_amount"})
    a["auction_gap"]=a.auction_price/a.prev_close_known-1
    a["auction_amount_to_prev_day"]=a.auction_amount/a.prev_day_amount
    a["auction_gap_x_volume"]=a.auction_gap*a.auction_volume_ratio20
    a["is_negative_gap"]=a.auction_gap<0
    a["is_high_auction_volume"]=a.auction_volume_ratio20>=1.5
    a["negative_gap_high_volume"]=a.is_negative_gap&a.is_high_auction_volume
    return a
def calc_auction_volume_ratio(current_volume:float, history:pd.Series, lookback:int=20)->float|None:
    clean=history.dropna().iloc[-lookback:]
    if len(clean)<lookback:return None
    median=float(clean.median()); return current_volume/median if median>0 else None
def score_auction(volume_ratio:float, gap:float, amount_to_prev:float)->float:
    if np.isnan(volume_ratio) or np.isnan(gap):return 0
    vs=0 if volume_ratio<1 else 3 if volume_ratio<1.5 else 5 if volume_ratio<2 else 8 if volume_ratio<3 else 10
    ps=6 if -.04<=gap<-.01 else 5 if -.01<=gap<=.01 else 3 if (-.06<=gap<-.04 or .01<gap<=.03) else 0
    aps=4 if amount_to_prev>=.05 else 2 if amount_to_prev>=.02 else 0
    return min(20.0,vs+ps+aps)
