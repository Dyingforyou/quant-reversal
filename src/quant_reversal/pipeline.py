"""Shared feature pipeline for research, backtest and scan."""
from datetime import date
import pandas as pd
from .config import AppConfig
from .data.base import DataProvider
from .features.auction import add_auction_features
from .features.break_structure import add_break_features
from .features.limitup import add_limit_up_features
from .features.ma import add_ma_reference
from .features.streak import add_streak_features
from .features.sector import active_members, best_sector, build_sector_scores
from .features.market import market_features
from .features.height import add_height_context
from .features.break_quality import add_break_quality
from .features.sentiment import add_market_sentiment
from .strategy.candidate import build_candidates
def daily_features(daily:pd.DataFrame,cfg:AppConfig)->pd.DataFrame:
    out=add_limit_up_features(daily,cfg.limitup.price_tolerance)
    out=add_streak_features(out)
    out=add_break_features(out,cfg.auction.lookback)
    out=add_height_context(out)
    out=add_break_quality(out,cfg.auction.lookback)
    out=add_market_sentiment(out)
    return add_ma_reference(out,cfg.ma5.lookback)
def candidates_for_date(provider:DataProvider,signal_date:date,cfg:AppConfig):
    daily=provider.get_daily_bars(date(1990,1,1),signal_date)
    # Signal-day daily bar is defensively removed, so changing its close cannot affect candidates.
    daily=daily[pd.to_datetime(daily.trade_date).dt.date<signal_date]
    auction=provider.get_auction(date(1990,1,1),signal_date)
    features=daily_features(daily,cfg); af=add_auction_features(auction,daily,cfg.auction.lookback)
    members=provider.get_sector_membership(signal_date)
    members=active_members(members,signal_date)
    latest=pd.to_datetime(features.trade_date).dt.date.max()
    previous=features[pd.to_datetime(features.trade_date).dt.date==latest]
    scores=build_sector_scores(previous,members)
    lookup={str(s):(best_sector(str(s),members,scores)) for s in previous.symbol}
    market=market_features(previous,auction,features).get("market_score",0)
    return build_candidates(signal_date,features,af,cfg,lookup,float(market))
