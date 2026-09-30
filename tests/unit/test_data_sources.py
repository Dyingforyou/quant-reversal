from datetime import date

import pandas as pd

from quant_reversal.data.akshare_source import AkshareIntradaySource
from quant_reversal.data.store import ParquetStore
from quant_reversal.data.tushare_source import TushareDailySource


class FakeAkshare:
    def stock_zh_a_hist_min_em(self, **kwargs):
        return pd.DataFrame({
            "时间": ["2026-08-17 09:30:00", "2026-08-17 09:31:00"],
            "开盘": [10, 10.1], "最高": [10.2, 10.2], "最低": [9.9, 10], "收盘": [10.1, 10.15],
            "成交量": [100, 120], "成交额": [1000, 1218],
        })

    def stock_zh_a_hist_pre_min_em(self, **kwargs):
        return pd.DataFrame({
            "时间": ["2026-08-17 09:24:00", "2026-08-17 09:25:00", "2026-08-17 09:30:00"],
            "收盘": [9.9, 10.0, 10.1], "成交量": [0, 500, 100], "成交额": [0, 5000, 1010],
        })


def test_akshare_uses_explicit_0925_auction_only():
    source = AkshareIntradaySource(FakeAkshare())
    frame = source.auction_snapshot(date(2026, 8, 17), ["000001.SZ"])
    assert len(frame) == 1
    assert frame.iloc[0].auction_volume == 500
    assert frame.iloc[0].source == "akshare_pre_min_09:25"


def test_akshare_does_not_substitute_first_minute_for_missing_auction():
    client = FakeAkshare()
    client.stock_zh_a_hist_pre_min_em = lambda **kwargs: pd.DataFrame({
        "时间": ["2026-08-17 09:30:00"], "收盘": [10.1], "成交量": [100], "成交额": [1010]
    })
    assert AkshareIntradaySource(client).auction_snapshot(date(2026, 8, 17), ["000001"]).empty


def test_parquet_store_upserts_by_primary_key(tmp_path):
    store = ParquetStore(tmp_path)
    first = pd.DataFrame({"trade_date": [date(2026, 8, 17)], "symbol": ["000001"], "close": [10.0]})
    second = first.assign(close=10.2)
    store.upsert("daily_bars", first, ["trade_date", "symbol"])
    store.upsert("daily_bars", second, ["trade_date", "symbol"])
    result = pd.read_parquet(tmp_path / "daily_bars.parquet")
    assert len(result) == 1
    assert result.iloc[0].close == 10.2


class FakeTushare:
    def trade_cal(self, **kwargs):
        return pd.DataFrame({"cal_date": ["20260817"], "is_open": [1]})

    def daily(self, **kwargs):
        return pd.DataFrame({"ts_code": ["000001.SZ"], "trade_date": ["20260817"], "open": [10], "high": [11], "low": [9.8], "close": [10.5], "pre_close": [10], "vol": [123], "amount": [456]})

    def stk_limit(self, **kwargs):
        return pd.DataFrame({"ts_code": ["000001.SZ"], "trade_date": ["20260817"], "up_limit": [11], "down_limit": [9]})

    def daily_basic(self, **kwargs):
        return pd.DataFrame({"ts_code": ["000001.SZ"], "trade_date": ["20260817"], "turnover_rate": [2.3]})

    def stock_basic(self, **kwargs):
        return pd.DataFrame({"ts_code": ["000001.SZ", "600001.SH"], "symbol": ["000001", "600001"], "name": ["平安银行", "*ST示例"], "market": ["主板", "主板"]})


def test_tushare_normalizes_daily_units():
    frame = TushareDailySource("unused", FakeTushare()).daily(date(2026, 8, 17), date(2026, 8, 17), ["000001"])
    assert frame.iloc[0].volume == 12300
    assert frame.iloc[0].amount == 456000
    assert frame.iloc[0].limit_up_price == 11


def test_tushare_universe_excludes_st():
    assert TushareDailySource("unused", FakeTushare()).universe() == ["000001"]


def test_tushare_security_master_keeps_real_name():
    frame = TushareDailySource("unused", FakeTushare()).security_master()
    assert frame.loc[frame.symbol == "000001", "name"].iloc[0] == "平安银行"
