from datetime import date
import pandas as pd
from quant_reversal.data.health import record_intraday_health


def test_health_records_missing_symbol_alert(tmp_path):
    pd.DataFrame({"trade_date":[date.today()],"symbol":["000001"],"minute":["00:00"]}).to_parquet(tmp_path/"minute_bars.parquet",index=False)
    result=record_intraday_health(tmp_path,date.today(),["000001","000002"])
    assert result["status"] == "stale"
    assert "000002" in result["stale_symbols"]
    assert (tmp_path/"realtime_alerts.jsonl").exists()
