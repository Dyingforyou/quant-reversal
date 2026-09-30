"""Trading-calendar helpers; never use natural-day arithmetic for strategy dates."""
from datetime import date
import pandas as pd

class TradingCalendar:
    def __init__(self, frame: pd.DataFrame):
        dates = pd.to_datetime(frame.loc[frame["is_open"].astype(bool), "trade_date"]).dt.date
        self.dates = tuple(sorted(set(dates)))
        self._index = {d: i for i, d in enumerate(self.dates)}
    def next(self, value: date, steps: int = 1) -> date:
        try: return self.dates[self._index[value] + steps]
        except (KeyError, IndexError) as exc: raise ValueError(f"no next trading day for {value}") from exc
    def previous(self, value: date, steps: int = 1) -> date:
        try:
            idx = self._index[value] - steps
            if idx < 0: raise IndexError
            return self.dates[idx]
        except (KeyError, IndexError) as exc: raise ValueError(f"no previous trading day for {value}") from exc
    def between(self, start: date, end: date) -> list[date]: return [d for d in self.dates if start <= d <= end]

