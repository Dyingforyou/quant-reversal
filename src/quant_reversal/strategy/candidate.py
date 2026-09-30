"""As-of 09:25 candidate construction using only prior daily bars and current auction."""
from datetime import date
import pandas as pd
from ..config import AppConfig
from ..features.auction import score_auction
from ..features.break_structure import score_break
from ..features.ma import score_ma5
from ..features.stock_strength import score_stock
from ..features.height import height_score
from ..features.sentiment import sentiment_score
from ..models import Candidate
from .scoring import finalize
def build_candidates(signal_date:date,daily_features:pd.DataFrame,auction_features:pd.DataFrame,cfg:AppConfig,sector_lookup:dict[str,tuple[str|None,float]]|None=None,market_score:float=0)->list[Candidate]:
    dates=sorted(pd.to_datetime(daily_features.trade_date).dt.date.unique()); prior=[d for d in dates if d<signal_date]
    if not prior:return []
    break_date=prior[-1]; rows=daily_features[pd.to_datetime(daily_features.trade_date).dt.date==break_date]
    rows=rows[rows.is_first_break & rows.prev_streak_height.between(cfg.candidate.research_min_board,cfg.candidate.research_max_board)]
    auction=auction_features[pd.to_datetime(auction_features.trade_date).dt.date==signal_date]
    result=[]
    for _,r in rows.merge(auction,on="symbol",suffixes=("","_auction")).iterrows():
        history=daily_features[(daily_features.symbol==r.symbol)&(pd.to_datetime(daily_features.trade_date).dt.date<=break_date)].sort_values("trade_date").close.tail(cfg.ma5.lookback)
        if len(history)<cfg.ma5.lookback:continue
        ma5_ref=float(history.mean());distance=r.auction_price/ma5_ref-1
        if cfg.candidate.hard_filter_ma5 and not cfg.ma5.min_distance<=distance<=cfg.ma5.max_distance:continue
        if cfg.candidate.hard_filter_auction and not cfg.auction.gap_min<=r.auction_gap<=cfg.auction.gap_max:continue
        sid,sector_score=(sector_lookup or {}).get(str(r.symbol),(None,0.0))
        amount_ratio=float(r.break_amount_ratio20) if pd.notna(r.break_amount_ratio20) else 0
        board_count=int(r.prev_streak_height);sub_strategy=str(r.sub_strategy)
        weights=cfg.models.low_height if sub_strategy=="LowHeightReversal" else cfg.models.mid_height if sub_strategy=="MidHeightReversal" else cfg.models.high_leader
        turnover_ratio=float(r.amount_ratio20_mean) if pd.notna(r.amount_ratio20_mean) else 0.0
        turnover_component=min(1.0,turnover_ratio/2) if turnover_ratio>0 else 0.0
        route_reason=f"{board_count}板属于{r.height_group}，路由至{sub_strategy}"
        raw_keys=["cycle_start_date","cycle_board_high","break_count_in_cycle","break_quality","break_max_drawdown","break_close_position","tail_support","turnover_rate","amount","amount_ratio20_mean","break_amount_ratio20","is_historical_record_amount","one_price_boards_in_cycle","turnover_boards_in_cycle","first_limit_time","last_limit_time","limit_break_count","sealed_duration_minutes","sealed_order_amount","sealed_order_to_float_cap","board_type","market_highest_board","prev_market_highest_board","market_advancement_rate","high_stock_next_day_premium","market_bust_rate","market_limit_down_count","market_board_stock_avg_return","previous_leader_today_return","auction_gap","auction_volume_ratio20","auction_amount_ratio20"]
        c=Candidate(signal_date=signal_date,symbol=str(r.symbol),best_sector_id=sid,prev_streak_height=board_count,is_first_break=True,ma5_ref=ma5_ref,ma5_distance_auction=float(distance),board_count=board_count,height_group=str(r.height_group),height_rank=int(r.height_rank),is_market_highest=bool(r.is_market_highest),same_height_count=int(r.same_height_count),sub_strategy=sub_strategy,model_route_reason=route_reason,sector_score=sector_score,stock_score=score_stock(board_count,.05,amount_ratio),break_score=score_break(True,float(r.break_close_position),amount_ratio,float(r.break_return)),ma5_score=score_ma5(distance),auction_score=score_auction(float(r.auction_volume_ratio20),float(r.auction_gap),float(r.auction_amount_to_prev_day)),market_score=market_score,height_score=height_score(board_count,int(r.height_rank),bool(r.is_market_highest)),turnover_score=turnover_component,sentiment_score=sentiment_score(r),reasons=[route_reason,f"断板质量：{r.break_quality}",f"MA5距离 {distance:+.2%}",f"竞价缺口 {r.auction_gap:+.2%}",f"竞价量比 {r.auction_volume_ratio20:.2f}x"],raw_features={k:r.get(k) for k in raw_keys})
        result.append(finalize(c,weights,cfg.score.grade_a,cfg.score.grade_b,cfg.score.watch))
    return result
