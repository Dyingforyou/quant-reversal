"""Fail-fast validation for normalized datasets."""
from pathlib import Path
import pandas as pd

DAILY = {"trade_date","symbol","open","high","low","close","prev_close","volume","amount","turnover_rate","limit_up_price","limit_down_price","is_trading"}
AUCTION = {"trade_date","symbol","auction_price","auction_volume","auction_amount"}
MINUTE = {"trade_date","symbol","minute","open","high","low","close","volume","amount"}
SECTOR = {"symbol","sector_id","sector_name","sector_type","effective_from","effective_to"}
CALENDAR = {"trade_date","is_open"}

class DataValidationError(ValueError): pass
def _columns(df, required, name):
    missing = required - set(df.columns)
    if missing: raise DataValidationError(f"{name}: missing fields {sorted(missing)}")
def validate_frames(daily, auction, minute, sector, calendar) -> dict:
    for df, cols, name in [(daily,DAILY,"daily_bars"),(auction,AUCTION,"auction"),(minute,MINUTE,"minute_bars"),(sector,SECTOR,"sector_membership"),(calendar,CALENDAR,"trading_calendar")]: _columns(df, cols, name)
    errors=[]; warnings=[]
    for df, keys, name in [(daily,["trade_date","symbol"],"daily_bars"),(auction,["trade_date","symbol"],"auction"),(minute,["trade_date","symbol","minute"],"minute_bars")]:
        if df.duplicated(keys).any(): errors.append(f"{name}: duplicate primary keys")
    if ((daily.low > daily.high)|(daily.open < daily.low)|(daily.open > daily.high)|(daily.close < daily.low)|(daily.close > daily.high)).any(): errors.append("daily_bars: invalid OHLC")
    if daily[["limit_up_price","limit_down_price"]].isna().any().any(): errors.append("daily_bars: missing limit prices")
    if (auction.auction_price <= 0).any(): errors.append("auction: invalid auction_price")
    if pd.to_datetime(minute.minute.astype(str),format="%H:%M",errors="coerce").isna().any(): warnings.append("minute_bars: non-standard minute values")
    s=sector.copy(); s["effective_from"]=pd.to_datetime(s.effective_from); s["effective_to"]=pd.to_datetime(s.effective_to).fillna(pd.Timestamp.max)
    for _, g in s.sort_values("effective_from").groupby(["symbol","sector_id"]):
        if len(g)>1 and (g.effective_from.iloc[1:].to_numpy() <= g.effective_to.iloc[:-1].to_numpy()).any(): errors.append("sector_membership: overlapping effective periods"); break
    open_dates=set(pd.to_datetime(calendar.loc[calendar.is_open,"trade_date"]).dt.date)
    data_dates=set(pd.to_datetime(daily.trade_date).dt.date)
    if data_dates-open_dates: errors.append("trading_calendar: daily dates missing")
    if errors: raise DataValidationError("; ".join(errors))
    return {"status":"ok","rows":{"daily":len(daily),"auction":len(auction),"minute":len(minute),"sector":len(sector)},"warnings":warnings}
def validate_directory(root: str | Path) -> dict:
    root=Path(root)
    return validate_frames(*(pd.read_parquet(root/f"{n}.parquet") for n in ["daily_bars","auction","minute_bars","sector_membership","trading_calendar"]))
