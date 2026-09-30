import pandas as pd
def active_members(members:pd.DataFrame, trade_date)->pd.DataFrame:
    point=pd.Timestamp(trade_date);start=pd.to_datetime(members.effective_from); end=pd.to_datetime(members.effective_to,errors="coerce")
    return members[(start<=point)&(end.isna()|(end>=point))].copy()
def build_sector_scores(daily_prev:pd.DataFrame, members:pd.DataFrame)->pd.DataFrame:
    x=members.merge(daily_prev,on="symbol",how="inner")
    x["ret"]=x.close/x.prev_close-1; x["advanced"]=x.ret>0
    rows=[]
    for sid,g in x.groupby("sector_id"):
        counts=g.limit_up_streak.clip(upper=4).value_counts()
        ladder=sum(k*counts.get(k,0) for k in range(1,5))
        rows.append({"sector_id":sid,"sector_limitup_count_prev":int(g.is_closed_limit_up.sum()),"sector_advance_ratio_prev":float(g.advanced.mean()),"sector_top5_return_median_prev":float(g.nlargest(min(5,len(g)),"ret").ret.median()),"ladder_raw":ladder})
    out=pd.DataFrame(rows)
    if out.empty:return out
    for col in ["sector_limitup_count_prev","sector_top5_return_median_prev","ladder_raw"]:out[col+"_pct"]=out[col].rank(pct=True)
    # MVP fixture has one sector; current-auction breadth is represented by the final 0~3 resonance component.
    out["sector_score"]=(5*out.sector_limitup_count_prev_pct+4*out.sector_advance_ratio_prev+4*out.sector_top5_return_median_prev_pct+4*out.ladder_raw_pct+3).clip(0,20)
    return out
def best_sector(symbol:str,members:pd.DataFrame,scores:pd.DataFrame)->tuple[str|None,float]:
    ids=members.loc[members.symbol==symbol,"sector_id"]; rows=scores[scores.sector_id.isin(ids)]
    if rows.empty:return None,0.0
    row=rows.sort_values(["sector_score","sector_id"],ascending=[False,True]).iloc[0]; return str(row.sector_id),float(row.sector_score)
