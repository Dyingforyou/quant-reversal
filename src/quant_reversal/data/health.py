"""Realtime data freshness checks and persistent alerts."""
from datetime import date, datetime, time, timedelta
from pathlib import Path
import json
import pandas as pd


def record_intraday_health(root: Path, trade_date: date, expected_symbols: list[str], max_delay_minutes: int = 3) -> dict:
    now = datetime.now().astimezone()
    path = root / "minute_bars.parquet"
    frame = pd.read_parquet(path) if path.exists() else pd.DataFrame()
    if not frame.empty:
        frame = frame[pd.to_datetime(frame.trade_date).dt.date == trade_date].copy()
    latest = {}
    for symbol in expected_symbols:
        rows = frame[frame.symbol.astype(str) == str(symbol)] if not frame.empty else frame
        latest[str(symbol)] = str(rows.minute.max()) if rows is not None and not rows.empty else None
    if now.time() >= time(15, 0):
        cutoff = "15:00"
    elif time(11, 30) <= now.time() < time(13, 0):
        cutoff = "11:30"
    else:
        cutoff = (now - timedelta(minutes=max_delay_minutes)).strftime("%H:%M")
    stale = [symbol for symbol, minute in latest.items() if minute is None or minute < cutoff]
    status = {"checked_at": now.isoformat(), "trade_date": trade_date.isoformat(), "status": "ok" if not stale else "stale", "latest_minute": latest, "stale_symbols": stale, "max_delay_minutes": max_delay_minutes}
    (root / "realtime_health.json").write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    if stale:
        with (root / "realtime_alerts.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(status, ensure_ascii=False) + "\n")
    return status
