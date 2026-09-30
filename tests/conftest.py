from datetime import date
import pandas as pd
import pytest

@pytest.fixture
def daily():
    closes=[10,10.1,10.2,11.22,12.34,12.0];rows=[]
    for i,c in enumerate(closes):
        prev=closes[i-1] if i else 10;limit=round(prev*1.1,2)
        rows.append(dict(trade_date=date(2024,1,2+i),symbol="X",open=prev,high=max(c,prev),low=min(c,prev),close=c,prev_close=prev,volume=1,amount=100,turnover_rate=1,limit_up_price=limit,limit_down_price=round(prev*.9,2),is_trading=True))
    return pd.DataFrame(rows)

