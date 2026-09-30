"""Persist idempotent progress for the 20-day market auction baseline."""
from datetime import date, datetime
from pathlib import Path
import json


def record_market_auction_progress(
    data_dir: Path,
    trade_date: date,
    received: int,
    universe: int,
    minimum_coverage: float = 0.8,
) -> dict:
    path = data_dir / "market_auction_progress.json"
    try:
        state = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except (json.JSONDecodeError, OSError):
        state = {}
    records = state.get("records", {})
    coverage = received / universe if universe else 0.0
    records[trade_date.isoformat()] = {
        "received": received,
        "universe": universe,
        "coverage": round(coverage, 6),
        "qualified": coverage >= minimum_coverage,
        "updated_at": datetime.now().astimezone().isoformat(),
    }
    qualified_days = sum(bool(item.get("qualified")) for item in records.values())
    result = {
        "target_days": 20,
        "qualified_days": qualified_days,
        "remaining_days": max(0, 20 - qualified_days),
        "records": dict(sorted(records.items())),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)
    return result


def load_market_auction_progress(data_dir: Path) -> dict:
    path = data_dir / "market_auction_progress.json"
    if not path.exists():
        return {"target_days": 20, "qualified_days": 0, "remaining_days": 20, "records": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"target_days": 20, "qualified_days": 0, "remaining_days": 20, "records": {}}
