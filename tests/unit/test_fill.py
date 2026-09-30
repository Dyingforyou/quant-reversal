from datetime import date,datetime,timedelta
from types import SimpleNamespace
from quant_reversal.backtest.broker import Broker
from quant_reversal.backtest.fill import try_fill
from quant_reversal.models import Order,Position,Side
def test_intraday_trigger_fills_next_bar():
    t=datetime(2024,1,1,9,35);o=Order(symbol="X",side=Side.BUY,quantity=100,created_at=t,earliest_fill_at=t+timedelta(minutes=1))
    assert try_fill(o,SimpleNamespace(timestamp=t,open=10,high=10.1,low=9.9),11,9) is None
    assert try_fill(o,SimpleNamespace(timestamp=t+timedelta(minutes=1),open=10,high=10.1,low=9.9),11,9).price==10
def test_locked_limits_and_t1():
    t=datetime(2024,1,1,9,36);buy=Order(symbol="X",side=Side.BUY,quantity=100,created_at=t,earliest_fill_at=t)
    assert try_fill(buy,SimpleNamespace(timestamp=t,open=11,high=11,low=11),11,9) is None
    pos=Position(symbol="X",quantity=100,entry_price=10,entry_date=t.date());assert not Broker().may_sell(pos,t.date());assert Broker().may_sell(pos,date(2024,1,2))

