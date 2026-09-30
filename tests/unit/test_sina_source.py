from datetime import date
import pandas as pd
from quant_reversal.data.sina_source import SinaIntradaySource


class Client:
    def stock_zh_a_minute(self, **kwargs):
        return pd.DataFrame({"day":["2026-08-19 09:30:00"],"open":[10],"high":[10.2],"low":[9.9],"close":[10.1],"volume":[1000],"amount":[10000]})


def test_sina_normalizes_full_ohlcv():
    frame=SinaIntradaySource(Client()).minute_bars(date(2026,8,19),["000001"])
    assert frame.iloc[0].minute == "09:30"
    assert frame.iloc[0].high == 10.2
    assert frame.iloc[0].quality == "full_ohlcv"
