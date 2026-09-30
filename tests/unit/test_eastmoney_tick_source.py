from datetime import date
import pandas as pd
from quant_reversal.data.eastmoney_tick_source import EastmoneyTickAuctionSource


class Client:
    def stock_intraday_em(self, **kwargs):
        return pd.DataFrame({"时间":["09:24:59","09:25:00","09:25:03"],"成交价":[9.9,10,10],"手数":[3,500,500],"买卖盘性质":["中性盘"]*3})


def test_tick_source_uses_explicit_auction_record_and_lot_units():
    frame=EastmoneyTickAuctionSource(Client()).auction_snapshot(date(2026,8,19),["600001"])
    assert len(frame)==1
    assert frame.iloc[0].auction_volume==50000
    assert frame.iloc[0].auction_amount==500000
