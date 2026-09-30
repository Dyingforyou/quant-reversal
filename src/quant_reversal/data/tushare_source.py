"""Tushare adapter for the daily datasets available to 2000-point members."""
from datetime import date
from typing import Any, Sequence

import pandas as pd

from .symbols import plain_symbol, tushare_symbol


class TushareDailySource:
    def __init__(self, token: str, client: Any | None = None):
        if client is None:
            try:
                import tushare as ts
            except ImportError as exc:
                raise RuntimeError('请先安装数据源依赖：pip install -e ".[data]"') from exc
            ts.set_token(token)
            client = ts.pro_api()
        self.client = client

    @staticmethod
    def _day(value: date) -> str:
        return value.strftime("%Y%m%d")

    def calendar(self, start: date, end: date) -> pd.DataFrame:
        raw = self.client.trade_cal(exchange="SSE", start_date=self._day(start), end_date=self._day(end))
        return pd.DataFrame({
            "trade_date": pd.to_datetime(raw["cal_date"], format="%Y%m%d").dt.date,
            "is_open": raw["is_open"].astype(bool),
        }).sort_values("trade_date").reset_index(drop=True)

    def universe(self) -> list[str]:
        raw = self.security_master()
        if raw.empty:
            return []
        # 策略不处理 ST/*ST；北交所涨跌停规则不同，也暂不纳入 MVP。
        selected = raw[~raw["name"].astype(str).str.contains("ST", case=False, na=False)]
        selected = selected[~selected["market"].astype(str).str.contains("北交所", na=False)]
        return sorted(selected["symbol"].astype(str).map(plain_symbol).unique().tolist())

    def security_master(self) -> pd.DataFrame:
        raw = self.client.stock_basic(exchange="", list_status="L", fields="ts_code,symbol,name,market")
        if raw.empty:
            return pd.DataFrame(columns=["symbol", "name", "market"])
        out = raw[["symbol", "name", "market"]].copy()
        out["symbol"] = out["symbol"].astype(str).map(plain_symbol)
        return out.drop_duplicates("symbol", keep="last").reset_index(drop=True)

    def daily(self, start: date, end: date, symbols: Sequence[str] | None = None) -> pd.DataFrame:
        frames: list[pd.DataFrame] = []
        requests: list[dict[str, str]] = []
        if symbols:
            requests = [{"ts_code": tushare_symbol(symbol), "start_date": self._day(start), "end_date": self._day(end)} for symbol in symbols]
        else:
            calendar = self.calendar(start, end)
            requests = [{"trade_date": self._day(day)} for day in calendar.loc[calendar.is_open, "trade_date"]]
        for kwargs in requests:
            daily = self.client.daily(**kwargs)
            if daily.empty:
                continue
            limit = self.client.stk_limit(**kwargs)
            basic = self.client.daily_basic(**kwargs, fields="ts_code,trade_date,turnover_rate")
            merged = daily.merge(limit[["ts_code", "trade_date", "up_limit", "down_limit"]], on=["ts_code", "trade_date"], how="left")
            merged = merged.merge(basic, on=["ts_code", "trade_date"], how="left")
            merged = merged.rename(columns={"vol": "volume", "up_limit": "limit_up_price", "down_limit": "limit_down_price"})
            merged["trade_date"] = pd.to_datetime(merged["trade_date"], format="%Y%m%d").dt.date
            merged["symbol"] = merged["ts_code"].map(plain_symbol)
            # Tushare daily volume is lots (手); the normalized contract uses shares.
            merged["volume"] = pd.to_numeric(merged["volume"]) * 100
            # Tushare daily amount is thousand yuan; the normalized contract uses yuan.
            merged["amount"] = pd.to_numeric(merged["amount"]) * 1000
            merged["is_trading"] = True
            frames.append(merged[["trade_date", "symbol", "open", "high", "low", "close", "pre_close", "volume", "amount", "turnover_rate", "limit_up_price", "limit_down_price", "is_trading"]].rename(columns={"pre_close": "prev_close"}))
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
