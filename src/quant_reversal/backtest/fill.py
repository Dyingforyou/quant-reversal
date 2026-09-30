"""A-share next-bar fill rules."""
from datetime import datetime
from ..models import Fill, Order, Side
def try_fill(order:Order,bar,limit_up_price:float,limit_down_price:float,slippage_bps:float=0,commission_bps:float=0,min_commission:float=0,sell_tax_bps:float=0)->Fill|None:
    timestamp=getattr(bar,"timestamp",None) or datetime.combine(getattr(bar,"trade_date"),datetime.strptime(str(getattr(bar,"minute")),"%H:%M").time())
    if timestamp<order.earliest_fill_at:return None
    locked_up=bar.open>=limit_up_price and bar.high==bar.low==limit_up_price
    locked_down=bar.open<=limit_down_price and bar.high==bar.low==limit_down_price
    if (order.side==Side.BUY and locked_up) or (order.side==Side.SELL and locked_down):return None
    direction=1 if order.side==Side.BUY else -1
    price=bar.open*(1+direction*slippage_bps/10000)
    price=min(price,limit_up_price) if order.side==Side.BUY else max(price,limit_down_price)
    value=price*order.quantity; commission=max(min_commission,value*commission_bps/10000); tax=value*sell_tax_bps/10000 if order.side==Side.SELL else 0
    return Fill(symbol=order.symbol,side=order.side,quantity=order.quantity,price=price,timestamp=timestamp,commission=commission,tax=tax)

