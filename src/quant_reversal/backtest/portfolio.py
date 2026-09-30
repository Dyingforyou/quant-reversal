import math
def order_quantity(cash:float,price:float,position_pct:float,lot_size:int=100)->int:
    return max(0,math.floor(cash*position_pct/price/lot_size)*lot_size)
def rank_candidates(frame):return frame.sort_values(["total_score","auction_score","sector_score","symbol"],ascending=[False,False,False,True])

