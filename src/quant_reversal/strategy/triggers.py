import pandas as pd
def is_intraday_confirmed(row:pd.Series,total_score:float,prev_close:float,ma5_ref:float,auction_price:float,min_volume_ratio:float=1.2,max_rebreak:int=1,min_score:float=70)->bool:
    base=(total_score>=min_score and row.close>=ma5_ref and row.open5m_volume_ratio20>=min_volume_ratio and row.rebreak_ma5_count<=max_rebreak)
    alternatives=((auction_price<prev_close and row.close>=prev_close) or row.close/auction_price-1>=.02 or (row.close/row.get("running_low",row.low)-1>=.03 and row.close>=ma5_ref))
    return bool(base and alternatives)
