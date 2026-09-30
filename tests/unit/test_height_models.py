from datetime import date

import pandas as pd

from quant_reversal.features.break_structure import add_break_features
from quant_reversal.features.height import add_height_context, strategy_for_height
from quant_reversal.features.limitup import add_limit_up_features
from quant_reversal.features.streak import add_streak_features


def test_strategy_router_covers_low_mid_and_high():
    assert strategy_for_height(2)[0] == "LowHeightReversal"
    assert strategy_for_height(4)[0] == "MidHeightReversal"
    assert strategy_for_height(8)[0] == "HighLeaderReversal"


def test_four_board_first_break_keeps_cycle_and_routes_mid():
    closes = [11.0, 12.1, 13.31, 14.64, 14.2]
    previous = [10.0, 11.0, 12.1, 13.31, 14.64]
    frame = pd.DataFrame(
        {
            "trade_date": [date(2026, 8, 17 + i) for i in range(5)],
            "symbol": ["600127"] * 5,
            "open": previous,
            "high": closes,
            "low": previous,
            "close": closes,
            "prev_close": previous,
            "limit_up_price": [11.0, 12.1, 13.31, 14.64, 16.1],
            "limit_down_price": [9.0, 9.9, 10.89, 11.98, 13.18],
            "amount": [100.0] * 5,
            "is_trading": [True] * 5,
        }
    )
    features = add_height_context(add_break_features(add_streak_features(add_limit_up_features(frame))))
    broken = features.iloc[-1]
    assert broken.is_first_break
    assert broken.board_count == 4
    assert broken.sub_strategy == "MidHeightReversal"
    assert broken.cycle_start_date == date(2026, 8, 17)
