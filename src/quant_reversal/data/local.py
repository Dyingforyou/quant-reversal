"""Local normalized Parquet provider."""
from datetime import date
from pathlib import Path
from typing import Sequence
import pandas as pd

class LocalParquetProvider:
    def __init__(self, root: str | Path): self.root = Path(root)
    def _read(self, name: str, required: bool = True) -> pd.DataFrame:
        path = self.root / f"{name}.parquet"
        if not path.exists():
            if required: raise FileNotFoundError(f"required normalized dataset missing: {path}")
            return pd.DataFrame()
        return pd.read_parquet(path)
    @staticmethod
    def _range(df: pd.DataFrame, start: date, end: date, symbols: Sequence[str] | None = None) -> pd.DataFrame:
        dates = pd.to_datetime(df["trade_date"]).dt.date
        out = df.loc[(dates >= start) & (dates <= end)].copy()
        if symbols is not None and "symbol" in out: out = out[out.symbol.astype(str).isin(map(str, symbols))]
        return out.reset_index(drop=True)
    def get_trading_calendar(self, start, end): return self._range(self._read("trading_calendar"), start, end)
    def get_daily_bars(self, start, end, symbols=None): return self._range(self._read("daily_bars"), start, end, symbols)
    def get_auction(self, start, end, symbols=None): return self._range(self._read("auction"), start, end, symbols)
    def get_minute_bars(self, trade_date, symbols=None): return self._range(self._read("minute_bars"), trade_date, trade_date, symbols)
    def get_sector_membership(self, trade_date, symbols=None):
        df = self._read("sector_membership")
        point = pd.Timestamp(trade_date)
        start = pd.to_datetime(df.effective_from)
        end = pd.to_datetime(df.effective_to, errors="coerce")
        out = df[(start <= point) & (end.isna() | (end >= point))].copy()
        if symbols is not None: out = out[out.symbol.astype(str).isin(map(str, symbols))]
        return out.reset_index(drop=True)
    def get_index_daily(self, start, end): return self._range(self._read("index_daily", False), start, end)
    def get_index_auction(self, trade_date): return self._range(self._read("index_auction", False), trade_date, trade_date)
