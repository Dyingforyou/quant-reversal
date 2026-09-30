"""Unauthenticated Tencent Finance intraday fallback source."""
from datetime import date, datetime, time
from typing import Any, Sequence

import pandas as pd

from .symbols import plain_symbol


class TencentIntradaySource:
    endpoint = "https://web.ifzq.gtimg.cn/appstock/app/minute/query"

    def __init__(self, session: Any | None = None):
        if session is None:
            import requests
            session = requests.Session()
        self.session = session

    @staticmethod
    def _code(value: str) -> str:
        symbol = plain_symbol(value)
        return ("sh" if symbol.startswith(("5", "6", "9")) else "sz") + symbol

    def _query(self, symbol: str) -> dict:
        code = self._code(symbol)
        response = self.session.get(self.endpoint, params={"code": code}, timeout=8)
        response.raise_for_status()
        payload = response.json()
        if payload.get("code") != 0 or code not in payload.get("data", {}):
            raise ValueError(f"腾讯行情返回异常: {code}")
        return payload["data"][code]

    def minute_bars(self, trade_date: date, symbols: Sequence[str]) -> pd.DataFrame:
        frames = []
        for value in symbols:
            symbol = plain_symbol(value)
            try:
                block = self._query(symbol)["data"]
            except Exception:
                continue
            returned_date = datetime.strptime(str(block["date"]), "%Y%m%d").date()
            if returned_date != trade_date:
                continue
            rows = []
            for item in block.get("data", []):
                parts = item.split()
                if len(parts) < 4:
                    continue
                rows.append((parts[0], float(parts[1]), float(parts[2]), float(parts[3])))
            if not rows:
                continue
            raw = pd.DataFrame(rows, columns=["minute", "price", "cum_volume", "cum_amount"])
            raw["volume"] = raw.cum_volume.diff().fillna(raw.cum_volume).clip(lower=0) * 100
            raw["amount"] = raw.cum_amount.diff().fillna(raw.cum_amount).clip(lower=0)
            frames.append(pd.DataFrame({
                "trade_date": trade_date, "symbol": symbol,
                "minute": raw.minute.str[:2] + ":" + raw.minute.str[2:],
                # Tencent minute feed exposes the minute price, not full OHLC.
                "open": raw.price, "high": raw.price, "low": raw.price, "close": raw.price,
                "volume": raw.volume, "amount": raw.amount,
                "source": "tencent_minute", "quality": "close_and_delta_volume",
                "ingested_at": datetime.now().astimezone().isoformat(),
            }))
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    def auction_snapshot(self, trade_date: date, symbols: Sequence[str]) -> pd.DataFrame:
        """Use the quote snapshot only during 09:25-09:29, when volume is auction volume."""
        now = datetime.now().astimezone()
        if now.date() != trade_date or not time(9, 25) <= now.time() < time(9, 30):
            return pd.DataFrame()
        rows = []
        for value in symbols:
            symbol = plain_symbol(value)
            try:
                quote = self._query(symbol)["qt"][self._code(symbol)]
                price, volume = float(quote[5]), float(quote[6]) * 100
                timestamp = datetime.strptime(quote[30], "%Y%m%d%H%M%S")
            except Exception:
                continue
            if timestamp.date() == trade_date and price > 0 and volume >= 0:
                rows.append({"trade_date": trade_date, "symbol": symbol, "auction_price": price, "auction_volume": volume, "auction_amount": price * volume, "source": "tencent_quote_09:25", "ingested_at": now.isoformat()})
        return pd.DataFrame(rows)
