from datetime import date
import pandas as pd
from ..calendar import TradingCalendar
from ..pipeline import candidates_for_date, daily_features
def build_samples(provider,cfg,start:date,end:date)->pd.DataFrame:
    cal=TradingCalendar(provider.get_trading_calendar(date(1990,1,1),date(2100,1,1)));rows=[]
    for day in cal.between(start,end):
        daily=provider.get_daily_bars(date(1990,1,1),day)
        prior=daily[pd.to_datetime(daily.trade_date).dt.date<day]
        if prior.empty:continue
        features=daily_features(prior,cfg);break_date=pd.to_datetime(features.trade_date).dt.date.max()
        research=features[(pd.to_datetime(features.trade_date).dt.date==break_date)&features.is_first_break&features.prev_streak_height.between(cfg.candidate.research_min_board,cfg.candidate.research_max_board)]
        scored={c.symbol:c for c in candidates_for_date(provider,day,cfg)}
        for _,sample in research.iterrows():
            symbol=str(sample.symbol);candidate=scored.get(symbol)
            row={"signal_date":day,"symbol":symbol,"research_pool":True,"scored_candidate":candidate is not None}
            row.update(sample.to_dict())
            if candidate:row.update({"total_score":candidate.total_score,"grade":candidate.grade,"sub_strategy":candidate.sub_strategy})
            rows.append(row)
    return pd.json_normalize(rows)
