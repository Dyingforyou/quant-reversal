def score_stock(prev_streak_height:int, sector_return_rank_pct:float, amount_ratio20:float)->float:
    height={2:6,3:10}.get(prev_streak_height,0)
    rank=5 if sector_return_rank_pct<=.05 else 4 if sector_return_rank_pct<=.10 else 2 if sector_return_rank_pct<=.20 else 0
    active=5 if 1.2<=amount_ratio20<=2.5 else 3 if .8<=amount_ratio20<1.2 else 2 if 2.5<amount_ratio20<=4 else 0
    return float(min(20,height+rank+active))

