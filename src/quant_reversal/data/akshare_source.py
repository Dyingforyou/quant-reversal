"""Free AKShare adapter for recent minute bars and the independent 09:25 snapshot."""
from datetime import date
from typing import Any, Sequence
import time

import pandas as pd

from .symbols import plain_symbol


class AkshareIntradaySource:
    def __init__(self, client: Any | None = None):
        if client is None:
            try:
                import akshare as ak
            except ImportError as exc:
                raise RuntimeError('请先安装数据源依赖：pip install -e ".[data]"') from exc
            client = ak
        self.client = client

    @staticmethod
    def _pick(frame: pd.DataFrame, *names: str) -> pd.Series:
        for name in names:
            if name in frame:
                return frame[name]
        raise ValueError(f"AKShare 返回缺少字段：{names}")

    @staticmethod
    def _retry(call, attempts: int = 3):
        error = None
        for index in range(attempts):
            try:
                return call()
            except Exception as exc:  # public web endpoints fail intermittently
                error = exc
                if index + 1 < attempts:
                    time.sleep(1.5 * (index + 1))
        raise error  # type: ignore[misc]

    def minute_bars(self, trade_date: date, symbols: Sequence[str]) -> pd.DataFrame:
        frames: list[pd.DataFrame] = []
        day = trade_date.strftime("%Y-%m-%d")
        for value in symbols:
            symbol = plain_symbol(value)
            try:
                raw = self._retry(lambda: self.client.stock_zh_a_hist_min_em(
                    symbol=symbol, start_date=f"{day} 09:30:00", end_date=f"{day} 15:00:00", period="1", adjust=""
                ))
            except Exception:
                continue
            if raw is None or raw.empty:
                continue
            timestamps = pd.to_datetime(self._pick(raw, "时间", "datetime"))
            mask = timestamps.dt.date == trade_date
            out = pd.DataFrame({
                "trade_date": timestamps[mask].dt.date,
                "symbol": symbol,
                "minute": timestamps[mask].dt.strftime("%H:%M"),
                "open": self._pick(raw, "开盘", "open")[mask].to_numpy(),
                "high": self._pick(raw, "最高", "high")[mask].to_numpy(),
                "low": self._pick(raw, "最低", "low")[mask].to_numpy(),
                "close": self._pick(raw, "收盘", "close")[mask].to_numpy(),
                "volume": self._pick(raw, "成交量", "volume")[mask].to_numpy(),
                "amount": self._pick(raw, "成交额", "amount")[mask].to_numpy(),
            })
            frames.append(out)
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    def auction_snapshot(self, trade_date: date, symbols: Sequence[str]) -> pd.DataFrame:
        """Read only an explicit 09:25 row; never substitute the first regular minute bar."""
        frames: list[dict[str, object]] = []
        for value in symbols:
            symbol = plain_symbol(value)
            try:
                raw = self._retry(lambda: self.client.stock_zh_a_hist_pre_min_em(symbol=symbol, start_time="09:15:00", end_time="09:29:59"))
            except Exception:
                continue
            if raw is None or raw.empty:
                continue
            timestamps = pd.to_datetime(self._pick(raw, "时间", "datetime"))
            selected = raw.loc[(timestamps.dt.date == trade_date) & (timestamps.dt.strftime("%H:%M") == "09:25")]
            if selected.empty:
                continue
            row = selected.iloc[-1]
            price = row.get("收盘", row.get("最新价", row.get("close")))
            volume = row.get("成交量", row.get("volume"))
            amount = row.get("成交额", row.get("amount"))
            if pd.isna(price) or pd.isna(volume):
                continue
            frames.append({"trade_date": trade_date, "symbol": symbol, "auction_price": float(price), "auction_volume": float(volume), "auction_amount": float(amount) if pd.notna(amount) else float(price) * float(volume), "source": "akshare_pre_min_09:25"})
        return pd.DataFrame(frames)
