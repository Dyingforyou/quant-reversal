"""Orchestrates the Tushare + AKShare hybrid collection workflow."""
from datetime import date
from collections.abc import Sequence
import json

from .store import ParquetStore
from .symbols import plain_symbol
from ..features.break_structure import add_break_features
from ..features.limitup import add_limit_up_features
from ..features.streak import add_streak_features
from ..features.height import add_height_context
from ..features.break_quality import add_break_quality
from ..features.sentiment import add_market_sentiment


def collect_daily(source, store: ParquetStore, start: date, end: date, symbols: Sequence[str] | None = None) -> dict[str, int]:
    calendar = source.calendar(start, end)
    daily = source.daily(start, end, symbols)
    result = {
        "trading_calendar": store.upsert("trading_calendar", calendar, ["trade_date"]),
        "daily_bars": store.upsert("daily_bars", daily, ["trade_date", "symbol"]),
    }
    if hasattr(source, "security_master"):
        result["security_master"] = store.upsert("security_master", source.security_master(), ["symbol"])
    return result


def base_pool(store: ParquetStore, signal_date: date, research_min_board: int = 2, research_max_board: int = 10):
    """Find the prior trading day's first-break stocks using daily data only."""
    import pandas as pd

    path = store.root / "daily_bars.parquet"
    if not path.exists():
        return pd.DataFrame(columns=["signal_date", "break_date", "symbol", "prev_streak_height"])
    daily = pd.read_parquet(path)
    prior = daily[pd.to_datetime(daily.trade_date).dt.date < signal_date]
    if prior.empty:
        return pd.DataFrame(columns=["signal_date", "break_date", "symbol", "prev_streak_height"])
    features = add_market_sentiment(add_break_quality(add_height_context(add_break_features(add_streak_features(add_limit_up_features(prior))))))
    break_date = pd.to_datetime(features.trade_date).dt.date.max()
    rows = features[(pd.to_datetime(features.trade_date).dt.date == break_date) & features.is_first_break & features.prev_streak_height.between(research_min_board, research_max_board)]
    columns=["trade_date","symbol","prev_streak_height","board_count","height_group","height_rank","is_market_highest","same_height_count","sub_strategy","cycle_start_date","cycle_board_high","break_count_in_cycle","is_first_break","break_quality","break_max_drawdown","break_close_position","tail_support","turnover_rate","amount","amount_ratio20_mean","break_amount_ratio20","is_historical_record_amount","one_price_boards_in_cycle","turnover_boards_in_cycle","first_limit_time","last_limit_time","limit_break_count","sealed_duration_minutes","sealed_order_amount","sealed_order_to_float_cap","board_type","market_highest_board","prev_market_highest_board","market_advancement_rate","high_stock_next_day_premium","market_bust_rate","market_limit_down_count","market_board_stock_avg_return","previous_leader_today_return"]
    result = rows[columns].copy()
    result.insert(0, "signal_date", signal_date)
    return result.rename(columns={"trade_date": "break_date"}).reset_index(drop=True)


def collect_intraday(source, store: ParquetStore, trade_date: date, symbols: Sequence[str], include_auction: bool = True) -> dict[str, int]:
    minute = source.minute_bars(trade_date, symbols)
    auction = source.auction_snapshot(trade_date, symbols) if include_auction else minute.iloc[0:0]
    result = {
        "minute_bars": store.upsert("minute_bars", minute, ["trade_date", "symbol", "minute"]),
        "auction": store.upsert("auction", auction, ["trade_date", "symbol"]),
    }
    expected = {plain_symbol(symbol) for symbol in symbols}
    missing = sorted(expected - set(auction.get("symbol", []))) if include_auction else []
    if missing:
        log = store.root / "collection_warnings.jsonl"
        with log.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"trade_date": trade_date.isoformat(), "type": "auction_no_data", "symbols": missing}, ensure_ascii=False) + "\n")
    return result


def collect_auction(source, store: ParquetStore, trade_date: date, symbols: Sequence[str]) -> dict[str, int]:
    """Collect only the explicit 09:25 snapshot for pre-open scanning."""
    auction = source.auction_snapshot(trade_date, symbols)
    rows = store.upsert("auction", auction, ["trade_date", "symbol"])
    expected = {plain_symbol(symbol) for symbol in symbols}
    missing = sorted(expected - set(auction.get("symbol", [])))
    from datetime import datetime
    health = {
        "checked_at": datetime.now().astimezone().isoformat(),
        "trade_date": trade_date.isoformat(),
        "status": "ok" if not missing else "incomplete",
        "expected": len(expected),
        "received": rows,
        "missing_symbols": missing,
        "sources": auction.groupby("source").size().to_dict() if "source" in auction else {},
    }
    (store.root / "auction_health.json").write_text(json.dumps(health, ensure_ascii=False, indent=2), encoding="utf-8")
    if missing:
        log = store.root / "collection_warnings.jsonl"
        with log.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"trade_date": trade_date.isoformat(), "type": "auction_no_data", "symbols": missing}, ensure_ascii=False) + "\n")
    return {"auction": rows, "auction_missing": len(missing), "auction_health": health["status"]}
