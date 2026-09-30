"""Explicit 09:25 auction record from Eastmoney intraday transaction details."""
from datetime import date, datetime
from typing import Any, Sequence
import time
import pandas as pd

from .symbols import plain_symbol


class EastmoneyTickAuctionSource:
    def __init__(self, client: Any | None = None):
        if client is None:
            import akshare as ak
            client = ak
        self.client = client

    def minute_bars(self, trade_date: date, symbols: Sequence[str]) -> pd.DataFrame:
        return pd.DataFrame()

    def auction_snapshot(self, trade_date: date, symbols: Sequence[str]) -> pd.DataFrame:
        rows = []
        for value in symbols:
            symbol = plain_symbol(value); raw = None
            for attempt in range(3):
                try:
                    raw = self.client.stock_intraday_em(symbol=symbol); break
                except Exception:
                    if attempt < 2: time.sleep(1.5 * (attempt + 1))
            if raw is None or raw.empty:
                continue
            selected = raw[raw["时间"].astype(str).str.startswith("09:25")].copy()
            if selected.empty:
                continue
            selected["手数"] = pd.to_numeric(selected["手数"], errors="coerce")
            row = selected.loc[selected["手数"].idxmax()]
            price, volume = float(row["成交价"]), float(row["手数"]) * 100
            if price > 0 and volume >= 0:
                rows.append({"trade_date":trade_date,"symbol":symbol,"auction_price":price,"auction_volume":volume,"auction_amount":price*volume,"source":"eastmoney_tick_09:25","ingested_at":datetime.now().astimezone().isoformat()})
        return pd.DataFrame(rows)
