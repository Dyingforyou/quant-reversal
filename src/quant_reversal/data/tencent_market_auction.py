"""Batch A-share 09:25 snapshots from Tencent's public quote endpoint."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, time
from typing import Any, Sequence
import re
import pandas as pd

from .symbols import plain_symbol


class TencentMarketAuctionSource:
    endpoint = "https://qt.gtimg.cn/q="

    def __init__(self, session: Any | None = None, now=None):
        if session is None:
            import requests
            session = requests.Session(); session.trust_env = False
        self.session = session; self.now = now or (lambda: datetime.now().astimezone())

    @staticmethod
    def _code(value: str) -> str:
        symbol=plain_symbol(value)
        prefix="bj" if symbol.startswith(("4","8","920")) else "sh" if symbol.startswith(("5","6","9")) else "sz"
        return prefix+symbol

    def _batch(self, symbols: Sequence[str]) -> list[dict]:
        codes=[self._code(x) for x in symbols]
        response=self.session.get(self.endpoint+",".join(codes),timeout=10)
        response.raise_for_status(); text=response.content.decode("gbk","replace"); rows=[]
        for match in re.finditer(r'v_(?:sh|sz|bj)\d+="([^"]*)";',text):
            fields=match.group(1).split("~")
            try:
                symbol=plain_symbol(fields[2]); price=float(fields[3]); volume=float(fields[6])*100
                timestamp=datetime.strptime(fields[30],"%Y%m%d%H%M%S")
            except (ValueError,IndexError):
                continue
            if price>0 and volume>=0:
                rows.append({"trade_date":timestamp.date(),"symbol":symbol,"auction_price":price,"auction_volume":volume,"auction_amount":price*volume,"source":"tencent_market_09:25","ingested_at":self.now().isoformat()})
        return rows

    def snapshot(self, trade_date: date, symbols: Sequence[str], batch_size: int=80, workers: int=8) -> pd.DataFrame:
        now=self.now()
        if now.date()!=trade_date or not time(9,25)<=now.time()<time(9,30):
            raise RuntimeError("全市场竞价快照只能在交易日09:25～09:29采集")
        batches=[symbols[i:i+batch_size] for i in range(0,len(symbols),batch_size)]; rows=[]
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures=[executor.submit(self._batch,batch) for batch in batches]
            for future in as_completed(futures):
                try: rows.extend(future.result())
                except Exception: continue
        frame=pd.DataFrame(rows)
        if not frame.empty:
            frame=frame[frame.trade_date==trade_date].drop_duplicates("symbol",keep="last")
        return frame.reset_index(drop=True)

    def opening_amounts(self, trade_date: date, symbols: Sequence[str], auction: pd.DataFrame) -> pd.DataFrame:
        """09:35 quote amount minus auction amount; keep the observed timestamp.

        This is a timed public-quote observation, not a fabricated minute bar.
        Both current and historical ratios must use this same measurement.
        """
        now = self.now()
        if now.date() != trade_date or not time(9, 35) <= now.time() < time(9, 36):
            raise RuntimeError("开盘5分钟全市场快照只能在09:35采集")
        baseline = dict(zip(auction.symbol.astype(str), auction.auction_amount))

        def collect(batch):
            response = self.session.get(self.endpoint + ",".join(self._code(s) for s in batch), timeout=10)
            response.raise_for_status()
            rows = []
            for match in re.finditer(r'v_(?:sh|sz|bj)\d+="([^"]*)";', response.content.decode("gbk", "replace")):
                fields = match.group(1).split("~")
                try:
                    symbol = plain_symbol(fields[2])
                    stamp = datetime.strptime(fields[30], "%Y%m%d%H%M%S")
                    amount = float(fields[37]) * 10000 - float(baseline[symbol])
                except (ValueError, IndexError, KeyError):
                    continue
                if stamp.date() == trade_date and time(9,35) <= stamp.time() < time(9,36) and amount > 0:
                    rows.append({"trade_date": trade_date, "symbol": symbol, "amount": amount,
                                 "source": "tencent_open5_quote", "observed_at": stamp.isoformat(),
                                 "ingested_at": self.now().isoformat()})
            return rows

        rows = []
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(collect, symbols[i:i+80]) for i in range(0,len(symbols),80)]
            for future in as_completed(futures):
                try:
                    rows.extend(future.result())
                except Exception:
                    continue
        return pd.DataFrame(rows)
