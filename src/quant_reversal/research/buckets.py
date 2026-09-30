import pandas as pd
def bucket_stats(samples:pd.DataFrame,factor:str,bins:list[float],target:str="next_day_1000_return")->pd.DataFrame:
    x=samples.copy();x["bucket"]=pd.cut(x[factor],bins=bins,include_lowest=True)
    def stats(g):
        r=g[target].dropna();win=r[r>0];loss=r[r<0]
        return pd.Series({"sample_count":len(r),"win_rate":(r>0).mean(),"mean_return":r.mean(),"median_return":r.median(),"avg_win":win.mean(),"avg_loss":loss.mean(),"win_loss_ratio":win.mean()/abs(loss.mean()) if len(win) and len(loss) else None,"profit_factor":win.sum()/abs(loss.sum()) if len(loss) else None,"mfe":g.get("mfe_1d",pd.Series(dtype=float)).mean(),"mae":g.get("mae_1d",pd.Series(dtype=float)).mean()})
    return x.groupby("bucket",observed=False).apply(stats,include_groups=False).reset_index()

