from datetime import date,datetime
from quant_reversal.data.tencent_market_auction import TencentMarketAuctionSource


class Response:
    content=('v_sz000001="51~平安银行~000001~10.10~10~10.10~500~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~20260821092601~";').encode('gbk')
    def raise_for_status(self): pass
class Session:
    def get(self,*args,**kwargs): return Response()


def test_market_snapshot_normalizes_lots_and_timestamp():
    now=lambda:datetime(2026,8,21,9,26,10)
    frame=TencentMarketAuctionSource(Session(),now).snapshot(date(2026,8,21),["000001"],workers=1)
    assert frame.iloc[0].auction_volume==50000
    assert frame.iloc[0].source=="tencent_market_09:25"
