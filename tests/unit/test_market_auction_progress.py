import json
from datetime import date

from quant_reversal.data.market_auction_progress import record_market_auction_progress


def test_progress_is_idempotent_and_only_counts_qualified_days(tmp_path):
    first = record_market_auction_progress(tmp_path, date(2026, 8, 21), 90, 100)
    repeated = record_market_auction_progress(tmp_path, date(2026, 8, 21), 95, 100)
    failed = record_market_auction_progress(tmp_path, date(2026, 8, 24), 70, 100)

    assert first["qualified_days"] == 1
    assert repeated["qualified_days"] == 1
    assert failed["qualified_days"] == 1
    assert failed["records"]["2026-08-24"]["qualified"] is False
    assert json.loads((tmp_path / "market_auction_progress.json").read_text())["remaining_days"] == 19
