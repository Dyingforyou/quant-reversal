import numpy as np
import pandas as pd

HEIGHT_BUCKETS=[("2板",2,2),("3板",3,3),("4板",4,4),("5板",5,5),("6板",6,6),("7板",7,7),("8板+",8,10_000)]

def calculate_height_layers(trades:pd.DataFrame)->list[dict]:
    rows=[]
    for label,lower,upper in HEIGHT_BUCKETS:
        group=trades[trades.board_count.between(lower,upper)] if not trades.empty and "board_count" in trades else pd.DataFrame()
        returns=group.return_pct.astype(float) if len(group) else pd.Series(dtype=float)
        wins=returns[returns>0];losses=returns[returns<0]
        rows.append({"height":label,"sample_count":len(group),"reversal_rate":float((group.d1_close_return>0).mean()) if len(group) and "d1_close_return" in group else None,"next_day_limit_up_rate":float(group.next_day_limit_up.mean()) if len(group) and "next_day_limit_up" in group else None,"d1_high_return":float(group.d1_high_return.mean()) if len(group) and "d1_high_return" in group else None,"d1_close_return":float(group.d1_close_return.mean()) if len(group) and "d1_close_return" in group else None,"mae":float(group.mae.mean()) if len(group) and "mae" in group else None,"mfe":float(group.mfe.mean()) if len(group) and "mfe" in group else None,"win_rate":float((returns>0).mean()) if len(returns) else None,"win_loss_ratio":float(wins.mean()/abs(losses.mean())) if len(wins) and len(losses) else None,"profit_factor":float(wins.sum()/abs(losses.sum())) if len(losses) else None})
    return rows
def calculate_metrics(trades:pd.DataFrame,initial_cash:float=1_000_000,no_fill_count:int=0,locked_count:int=0)->dict:
    if trades.empty:return {"total_return":0.0,"trade_count":0,"no_fill_count":no_fill_count,"locked_limit_down_exit_count":locked_count,"height_layers":calculate_height_layers(trades)}
    r=trades.return_pct.astype(float); equity=(1+r).cumprod(); draw=equity/equity.cummax()-1; wins=r[r>0]; losses=r[r<0]
    return {"total_return":float(equity.iloc[-1]-1),"annualized_return":float((equity.iloc[-1]**(252/max(1,len(r)))-1)),"max_drawdown":float(draw.min()),"sharpe_like_ratio":float(r.mean()/r.std(ddof=1)*np.sqrt(len(r))) if len(r)>1 and r.std()>0 else 0,"trade_count":len(r),"win_rate":float((r>0).mean()),"avg_trade_return":float(r.mean()),"median_trade_return":float(r.median()),"avg_win":float(wins.mean()) if len(wins) else 0,"avg_loss":float(losses.mean()) if len(losses) else 0,"win_loss_ratio":float(wins.mean()/abs(losses.mean())) if len(wins) and len(losses) else 0,"profit_factor":float(wins.sum()/abs(losses.sum())) if len(losses) else float("inf"),"max_consecutive_losses":_run(r<0),"max_consecutive_wins":_run(r>0),"avg_holding_days":float(trades.holding_days.mean()),"turnover":float((trades.entry_price*trades.quantity).sum()/initial_cash),"no_fill_count":no_fill_count,"locked_limit_down_exit_count":locked_count,"height_layers":calculate_height_layers(trades)}
def _run(values):
    best=cur=0
    for x in values:cur=cur+1 if x else 0;best=max(best,cur)
    return best
