"""Deterministic synthetic data; it is not a claim about real performance."""
from pathlib import Path
import pandas as pd
def generate(root:Path):
    root.mkdir(parents=True,exist_ok=True);dates=pd.bdate_range("2024-01-02",periods=35);symbols=["000001","000002","000003","000004","000005"]
    rows=[]
    for si,symbol in enumerate(symbols):
        prev=10+si
        for i,d in enumerate(dates):
            limit=round(prev*1.10,2);down=round(prev*.90,2);close=round(prev*(1+.002*((i%3)-1)),2);op=prev;high=max(op,close)*1.01;low=min(op,close)*.99
            if i in (25,26):
                close=high=limit
                if symbol=="000003":op=low=limit
                else:op=low=prev
            if i==27:
                if symbol=="000005":op=prev;close=high=limit;low=prev
                else:op=prev*.97;close=prev*.98;high=prev*1.02;low=prev*.95
            rows.append(dict(trade_date=d.date(),symbol=symbol,open=op,high=high,low=low,close=close,prev_close=prev,volume=1e6,amount=1e7*(1+i%4/10),turnover_rate=2.0,limit_up_price=limit,limit_down_price=down,is_trading=True,is_st=False));prev=close
    daily=pd.DataFrame(rows);daily.to_parquet(root/"daily_bars.parquet",index=False)
    auctions=[];minutes=[]
    for si,symbol in enumerate(symbols):
        for i,d in enumerate(dates):
            row=daily[(daily.symbol==symbol)&(daily.trade_date==d.date())].iloc[0];price=row.prev_close*(.98 if i==28 else 1);vol=100000 if i==28 else 10000;auctions.append(dict(trade_date=d.date(),symbol=symbol,auction_price=price,auction_volume=vol,auction_amount=vol*price,bid_unmatched_amount=None,ask_unmatched_amount=None))
            for m in pd.date_range(f"{d.date()} 09:30",f"{d.date()} 10:02",freq="min"):
                k=(m.hour*60+m.minute)-(9*60+30);p=price*(1+.0015*k if i==28 and symbol=="000001" else 1);minutes.append(dict(trade_date=d.date(),symbol=symbol,minute=m.strftime("%H:%M"),open=p,high=p*1.002,low=p*.998,close=p*1.001,volume=20000,amount=20000*p))
    pd.DataFrame(auctions).to_parquet(root/"auction.parquet",index=False);pd.DataFrame(minutes).to_parquet(root/"minute_bars.parquet",index=False)
    members=pd.DataFrame([dict(symbol=s,sector_id="S1",sector_name="合成板块",sector_type="concept",effective_from=dates[0].date(),effective_to=None) for s in symbols]);members.to_parquet(root/"sector_membership.parquet",index=False)
    pd.DataFrame({"trade_date":dates.date,"is_open":True}).to_parquet(root/"trading_calendar.parquet",index=False)
