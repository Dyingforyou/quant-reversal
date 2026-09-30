import pandas as pd
def market_features(previous:pd.DataFrame,current_auction:pd.DataFrame,history:pd.DataFrame)->dict:
    limitups=previous[previous.is_closed_limit_up]
    premium=current_auction.merge(limitups[["symbol","close"]],on="symbol",how="inner")
    premium_value=float((premium.auction_price/premium.close-1).mean()) if len(premium) else 0.0
    counts=history.groupby("trade_date").is_closed_limit_up.sum()
    current=int(previous.is_closed_limit_up.sum()); pct=float((counts<=current).mean()) if len(counts) else .5
    down=int((previous.close<=previous.limit_down_price+.001).sum())
    return {"prev_market_limitup_count":current,"prev_market_limitdown_count":down,"prev_market_max_streak":int(previous.limit_up_streak.max()),"prev_limitup_basket_auction_premium":premium_value,"market_score":min(10,3*pct+max(0,2-down/5)+(3 if premium_value>0 else 1)+min(2,previous.limit_up_streak.max()/2))}

