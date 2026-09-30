import pandas as pd
from quant_reversal.features.limitup import add_limit_up_features
from quant_reversal.features.streak import add_streak_features
from quant_reversal.features.break_structure import add_break_features
from quant_reversal.features.ma import add_ma_reference
from quant_reversal.features.auction import calc_auction_volume_ratio
def test_limit_up_streak_and_first_break(daily):
    x=add_break_features(add_streak_features(add_limit_up_features(daily)))
    assert list(x.limit_up_streak[-3:])==[1,2,0]
    assert bool(x.iloc[-1].is_first_break) and x.iloc[-1].prev_streak_height==2
def test_touch_not_close_is_not_streak(daily):
    daily.loc[3,"high"]=daily.loc[3,"limit_up_price"];daily.loc[3,"close"]=daily.loc[3,"prev_close"]
    assert not add_limit_up_features(daily).iloc[3].is_closed_limit_up
def test_ma_reference_excludes_signal_day(daily):
    x=add_ma_reference(daily,5);expected=daily.close.iloc[:5].mean();assert x.iloc[5].ma5_ref==expected
    changed=daily.copy();changed.loc[5,"close"]=999;assert add_ma_reference(changed,5).iloc[5].ma5_ref==expected
def test_auction_baseline_excludes_current():
    assert calc_auction_volume_ratio(100,pd.Series(range(1,21)),20)==100/10.5
    assert calc_auction_volume_ratio(100,pd.Series(range(1,20)),20) is None

