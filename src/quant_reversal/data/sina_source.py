"""Sina Finance minute bars exposed through AKShare."""
from datetime import date, datetime
from typing import Any, Sequence
import pandas as pd

from .symbols import plain_symbol


class SinaIntradaySource:
    def __init__(self, client: Any | None = None):
        if client is None:
            import akshare as ak
            client = ak
        self.client = client

    @staticmethod
    def _code(value: str) -> str:
        symbol = plain_symbol(value)
        return ("sh" if symbol.startswith(("5", "6", "9")) else "sz") + symbol

    def minute_bars(self, trade_date: date, symbols: Sequence[str]) -> pd.DataFrame:
        frames = []
        for value in symbols:
            symbol = plain_symbol(value)
            try:
                raw = self.client.stock_zh_a_minute(symbol=self._code(symbol), period="1", adjust="")
            except Exception:
                continue
            if raw is None or raw.empty:
                continue
            timestamps = pd.to_datetime(raw["day"])
            selected = raw.loc[timestamps.dt.date == trade_date].copy()
            timestamps = timestamps.loc[selected.index]
            if selected.empty:
                continue
            frames.append(pd.DataFrame({
                "trade_date": timestamps.dt.date, "symbol": symbol,
                "minute": timestamps.dt.strftime("%H:%M"),
                "open": pd.to_numeric(selected["open"]).to_numpy(),
                "high": pd.to_numeric(selected["high"]).to_numpy(),
                "low": pd.to_numeric(selected["low"]).to_numpy(),
                "close": pd.to_numeric(selected["close"]).to_numpy(),
                "volume": pd.to_numeric(selected["volume"]).to_numpy(),
                "amount": pd.to_numeric(selected["amount"]).to_numpy(),
                "source": "sina_minute", "quality": "full_ohlcv",
                "ingested_at": datetime.now().astimezone().isoformat(),
            }))
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    def auction_snapshot(self, trade_date: date, symbols: Sequence[str]) -> pd.DataFrame:
        return pd.DataFrame()
