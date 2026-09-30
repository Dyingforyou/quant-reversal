from datetime import date

from quant_reversal.data.tencent_source import TencentIntradaySource


class Response:
    def raise_for_status(self): pass
    def json(self):
        return {"code": 0, "data": {"sz000001": {"data": {"date": "20260819", "data": ["0930 10.00 100 100000.00", "0931 10.10 160 160600.00"]}}}}


class Session:
    def get(self, *args, **kwargs): return Response()


def test_tencent_cumulative_volume_becomes_per_minute_shares():
    frame = TencentIntradaySource(Session()).minute_bars(date(2026, 8, 19), ["000001"])
    assert frame.minute.tolist() == ["09:30", "09:31"]
    assert frame.volume.tolist() == [10000, 6000]
    assert frame.amount.tolist() == [100000, 60600]
    assert frame.source.unique().tolist() == ["tencent_minute"]
