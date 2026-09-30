"""Point-in-time industry snapshots and exchange-provided price limits."""
from datetime import date, datetime, timedelta
from pathlib import Path
import pandas as pd

from .store import ParquetStore
from .symbols import plain_symbol


def collect_reference(source, root: Path, trade_date: date) -> dict:
    raw = source.client.stock_basic(exchange="", list_status="L", fields="ts_code,symbol,industry")
    if raw.empty or "industry" not in raw:
        raise RuntimeError("未取得真实行业成员数据")
    raw = raw.dropna(subset=["industry"])
    observed = date.today()  # Never backfill today's membership into past dates.
    incoming = pd.DataFrame({"symbol": raw.symbol.map(plain_symbol),
                             "sector_id": "industry:" + raw.industry.astype(str),
                             "sector_name": raw.industry.astype(str), "sector_type": "industry",
                             "effective_from": observed, "effective_to": None,
                             "source": "tushare_stock_basic",
                             "observed_at": datetime.now().astimezone().isoformat()})
    path = root / "sector_membership.parquet"
    if path.exists():
        old = pd.read_parquet(path)
        # Same-day retries replace that day's snapshot, while earlier snapshots
        # end on the day before the next observation becomes valid.
        old = old[pd.to_datetime(old.effective_from).dt.date < observed].copy()
        old.loc[old.effective_to.isna(), "effective_to"] = observed - timedelta(days=1)
        incoming = pd.concat([old, incoming], ignore_index=True)
    temporary = path.with_suffix(".parquet.tmp")
    incoming.to_parquet(temporary, index=False)
    temporary.replace(path)
    limits = source.client.stk_limit(trade_date=trade_date.strftime("%Y%m%d"))
    if limits.empty:
        raise RuntimeError("未取得当日真实涨跌停价")
    limits = limits.rename(columns={"up_limit":"limit_up_price", "down_limit":"limit_down_price"})
    limits["symbol"] = limits.ts_code.map(plain_symbol)
    limits["trade_date"] = pd.to_datetime(limits.trade_date, format="%Y%m%d").dt.date
    limits = limits[["trade_date", "symbol", "limit_up_price", "limit_down_price"]].dropna()
    count = ParquetStore(root).upsert("price_limits", limits, ["trade_date", "symbol"])
    return {"sector_members": len(raw), "price_limits": count, "membership_effective_from": str(observed)}
