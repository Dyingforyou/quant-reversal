"""Conservative event backtest with next-bar entry and T+1 fixed exit."""
from datetime import date,datetime
import pandas as pd
from ..calendar import TradingCalendar
from ..models import Order,Side
from ..pipeline import candidates_for_date
from ..features.intraday import intraday_snapshots
from ..strategy.triggers import is_intraday_confirmed
from .fill import try_fill
from .metrics import calculate_metrics
from .portfolio import order_quantity,rank_candidates
def run_backtest(provider,cfg,start:date,end:date)->tuple[pd.DataFrame,dict]:
    cal=TradingCalendar(provider.get_trading_calendar(date(1990,1,1),date(2100,1,1))); trades=[];no_fill=0;locked=0;cash=cfg.backtest.initial_cash
    for day in cal.between(start,end):
        candidates=candidates_for_date(provider,day,cfg)
        if not candidates:continue
        ranked=rank_candidates(pd.DataFrame([c.model_dump() for c in candidates])).head(cfg.backtest.max_positions)
        for c in ranked.itertuples():
            bars=provider.get_minute_bars(day,[c.symbol]);daily=provider.get_daily_bars(date(1990,1,1),day,[c.symbol]).sort_values("trade_date")
            prior=daily[pd.to_datetime(daily.trade_date).dt.date<day]
            if bars.empty or prior.empty:continue
            prev=float(prior.iloc[-1].close);auction=float(provider.get_auction(day,day,[c.symbol]).iloc[0].auction_price)
            snap=intraday_snapshots(bars,prev,c.ma5_ref,auction,pd.Series([bars.amount.iloc[:5].sum()/2]*20));snap["running_low"]=snap.low.cummin()
            trigger=None
            for i,row in snap.iterrows():
                if is_intraday_confirmed(row,c.total_score,prev,c.ma5_ref,auction):trigger=i;break
            if trigger is None or trigger+1>=len(snap):continue
            nextbar=snap.iloc[trigger+1];ts=datetime.combine(day,datetime.strptime(str(nextbar.minute),"%H:%M").time());qty=order_quantity(cash,float(nextbar.open),cfg.backtest.position_size_pct,cfg.backtest.lot_size)
            order=Order(symbol=c.symbol,side=Side.BUY,quantity=qty,created_at=datetime.combine(day,datetime.strptime(str(snap.iloc[trigger].minute),"%H:%M").time()),earliest_fill_at=ts)
            entry=try_fill(order,nextbar,float(daily.iloc[-1].limit_up_price),float(daily.iloc[-1].limit_down_price),cfg.entry.slippage_bps,cfg.costs.commission_bps,cfg.costs.min_commission,cfg.costs.sell_tax_bps)
            if not entry:no_fill+=1;continue
            try:exit_day=cal.next(day)
            except ValueError:continue
            eb=provider.get_minute_bars(exit_day,[c.symbol]).sort_values("minute");dd=provider.get_daily_bars(exit_day,exit_day,[c.symbol])
            if eb.empty or dd.empty:continue
            target=eb[eb.minute.astype(str)>"10:00"]
            if target.empty:continue
            exit_fill=None
            for _,bar in target.iterrows():
                ets=datetime.combine(exit_day,datetime.strptime(str(bar.minute),"%H:%M").time());sell=Order(symbol=c.symbol,side=Side.SELL,quantity=qty,created_at=ets,earliest_fill_at=ets)
                exit_fill=try_fill(sell,bar,float(dd.iloc[0].limit_up_price),float(dd.iloc[0].limit_down_price),cfg.entry.slippage_bps,cfg.costs.commission_bps,cfg.costs.min_commission,cfg.costs.sell_tax_bps)
                if exit_fill:break
                locked+=1
            if exit_fill:
                costs=entry.commission+exit_fill.commission+exit_fill.tax;ret=(exit_fill.price*qty-costs)/(entry.price*qty)-1
                d1=dd.iloc[0];d1_high=float(d1.high/entry.price-1);d1_close=float(d1.close/entry.price-1);mae=float(d1.low/entry.price-1)
                trades.append({"symbol":c.symbol,"board_count":int(c.board_count),"height_group":c.height_group,"sub_strategy":c.sub_strategy,"entry_time":entry.timestamp,"entry_price":entry.price,"exit_time":exit_fill.timestamp,"exit_price":exit_fill.price,"quantity":qty,"costs":costs,"return_pct":ret,"d1_high_return":d1_high,"d1_close_return":d1_close,"mae":mae,"mfe":d1_high,"next_day_limit_up":bool(d1.close>=d1.limit_up_price-.001),"holding_days":1,"score_grade":c.grade})
    frame=pd.DataFrame(trades);return frame,calculate_metrics(frame,cfg.backtest.initial_cash,no_fill,locked)
