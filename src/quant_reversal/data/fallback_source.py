"""Merge free intraday sources per symbol, preferring the first usable result."""
from datetime import date
from typing import Sequence
import pandas as pd

from .symbols import plain_symbol


class FallbackIntradaySource:
    def __init__(self, sources): self.sources = list(sources)

    def _collect(self, method: str, trade_date: date, symbols: Sequence[str]) -> pd.DataFrame:
        remaining = [plain_symbol(x) for x in symbols]; frames = []
        for source in self.sources:
            if not remaining: break
            try: frame = getattr(source, method)(trade_date, remaining)
            except Exception: continue
            if frame is None or frame.empty: continue
            frames.append(frame); found = set(frame.symbol.astype(str)); remaining = [x for x in remaining if x not in found]
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    def minute_bars(self, trade_date, symbols): return self._collect("minute_bars", trade_date, symbols)
    def auction_snapshot(self, trade_date, symbols): return self._collect("auction_snapshot", trade_date, symbols)
