from datetime import date
import pandas as pd
from quant_reversal.calendar import TradingCalendar
from quant_reversal.features.sector import active_members
def test_calendar_uses_trading_day_not_calendar_day():
    c=TradingCalendar(pd.DataFrame({"trade_date":[date(2024,1,5),date(2024,1,8)],"is_open":[1,1]}));assert c.next(date(2024,1,5))==date(2024,1,8)
def test_sector_membership_is_point_in_time():
    m=pd.DataFrame({"symbol":["X","X"],"sector_id":["OLD","NEW"],"effective_from":[date(2020,1,1),date(2024,1,1)],"effective_to":[date(2023,12,31),None]})
    assert active_members(m,date(2023,1,1)).sector_id.tolist()==["OLD"]

