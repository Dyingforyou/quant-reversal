from datetime import date
import json
import pandas as pd

from quant_reversal.data.collector import collect_auction
from quant_reversal.data.store import ParquetStore


class PartialSource:
    def auction_snapshot(self, trade_date, symbols):
        return pd.DataFrame([{"trade_date":trade_date,"symbol":"000001","auction_price":10.0,"auction_volume":1000,"auction_amount":10000,"source":"test"}])


def test_auction_health_reports_source_and_missing_symbol(tmp_path):
    result=collect_auction(PartialSource(),ParquetStore(tmp_path),date(2026,8,20),["000001","000002"])
    health=json.loads((tmp_path/"auction_health.json").read_text())
    assert result["auction_health"] == "incomplete"
    assert health["sources"] == {"test":1}
    assert health["missing_symbols"] == ["000002"]
