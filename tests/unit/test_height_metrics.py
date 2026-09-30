import pandas as pd

from quant_reversal.backtest.metrics import calculate_height_layers


def test_height_layers_always_include_required_buckets():
    trades = pd.DataFrame(
        [
            {"board_count": 4, "return_pct": 0.1, "d1_close_return": 0.05, "next_day_limit_up": True, "d1_high_return": 0.1, "mae": -0.02, "mfe": 0.1},
            {"board_count": 8, "return_pct": -0.05, "d1_close_return": -0.03, "next_day_limit_up": False, "d1_high_return": 0.01, "mae": -0.08, "mfe": 0.01},
        ]
    )
    layers = calculate_height_layers(trades)
    assert [row["height"] for row in layers] == ["2板", "3板", "4板", "5板", "6板", "7板", "8板+"]
    assert next(row for row in layers if row["height"] == "4板")["sample_count"] == 1
    assert next(row for row in layers if row["height"] == "8板+")["sample_count"] == 1
