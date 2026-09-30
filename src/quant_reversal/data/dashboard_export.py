"""Publish only collected real data as static dashboard JSON."""
from datetime import date, datetime, time
from pathlib import Path
import json

import pandas as pd

from .market_auction_progress import load_market_auction_progress
from .dashboard_paper_export import publish_dashboard  # Active real paper-account publisher.


def _write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def _legacy_collection_dashboard(data_dir: Path, public_dir: Path, trade_date: date) -> dict[str, int]:
    """Legacy collection-only layout; retained for reference, never called live."""
    pool_path = data_dir / f"base_pool_{trade_date.strftime('%Y%m%d')}.csv"
    pool = pd.read_csv(pool_path, dtype={"symbol": str}) if pool_path.exists() else pd.DataFrame()
    daily = pd.read_parquet(data_dir / "daily_bars.parquet")
    minute_path = data_dir / "minute_bars.parquet"
    auction_path = data_dir / "auction.parquet"
    minute = pd.read_parquet(minute_path) if minute_path.exists() else pd.DataFrame()
    auction = pd.read_parquet(auction_path) if auction_path.exists() else pd.DataFrame()
    master_path = data_dir / "security_master.parquet"
    master = pd.read_parquet(master_path) if master_path.exists() else pd.DataFrame()
    names = dict(zip(master.symbol.astype(str), master.name.astype(str))) if not master.empty else {}
    minute_today = minute[pd.to_datetime(minute.trade_date).dt.date == trade_date] if not minute.empty else minute
    auction_today = auction[pd.to_datetime(auction.trade_date).dt.date == trade_date] if not auction.empty else auction
    latest = daily[pd.to_datetime(daily.trade_date).dt.date == pd.to_datetime(daily.trade_date).dt.date.max()]
    minute_symbols = set(minute_today.symbol.astype(str)) if not minute_today.empty else set()
    all_auction_symbols = set(auction_today.symbol.astype(str)) if not auction_today.empty else set()
    pool_symbols = set(pool.symbol.astype(str).str.zfill(6)) if not pool.empty else set()
    auction_symbols = all_auction_symbols & pool_symbols
    auction_sources = ", ".join(sorted(auction_today.source.dropna().astype(str).unique())) if "source" in auction_today else "无"
    candidates = []
    pipeline = []
    for row in pool.itertuples():
        symbol = str(row.symbol).zfill(6)
        has_minute = symbol in minute_symbols
        has_auction = symbol in auction_symbols
        status = "WATCH" if has_minute else "NO_DATA"
        name = names.get(symbol, "名称待更新")
        board_count = int(getattr(row, "board_count", row.prev_streak_height))
        height_group = str(getattr(row, "height_group", "低位反包" if board_count <= 3 else "中位反包" if board_count <= 5 else "高标反包"))
        sub_strategy = str(getattr(row, "sub_strategy", "LowHeightReversal" if board_count <= 3 else "MidHeightReversal" if board_count <= 5 else "HighLeaderReversal"))
        height_rank = int(getattr(row, "height_rank", 0))
        market_highest = bool(getattr(row, "is_market_highest", False))
        route_reason = f"{board_count}板属于{height_group}，路由至{sub_strategy}"
        candidate = {"symbol": symbol, "name": name, "status": status, "score": 0, "grade": "—", "board_count": board_count, "board_height": board_count, "height_group": height_group, "height_rank": height_rank, "market_highest": market_highest, "sub_strategy": sub_strategy, "sector_name": "暂无真实板块数据", "sector_score": 0, "ma5_distance": 0, "auction_score": 0, "auction_volume_ratio": 0, "intraday_status": "PASS" if has_minute else "NO_DATA", "primary_reason": "已采集盘中分钟线，等待竞价历史基线" if has_minute else "免费接口未返回分钟数据"}
        candidates.append(candidate)
        pipeline.append({"trade_date": trade_date.isoformat(), "symbol": symbol, "name": name, "board_height": board_count, "height_group": height_group, "height_rank": height_rank, "market_highest": market_highest, "sub_strategy": sub_strategy, "model_route_reason": route_reason, "final_status": status, "current_stage": "Intraday" if has_minute else "Auction", "stage_statuses": {"BoardHeightDetection": "PASS", "StrategyRouter": "PASS", "HeightModel": "PASS", "BoardPattern": "PASS", "FirstBreak": "PASS", "Sector": "NO_DATA", "MA5": "NOT_RUN", "Auction": "PASS" if has_auction else "NO_DATA", "Intraday": "PASS" if has_minute else "NO_DATA"}, "total_score": None, "grade": "—", "rejection_stage": None, "rejection_rule": None, "rejection_reason": candidate["primary_reason"], "updated_at": str(minute_today.minute.max()) if has_minute else "09:26"})
        stages = [
            {"stage_id":"board-height","stage_name":"BoardHeightDetection","status":"PASS","score":None,"max_score":None,"rules":[{"rule_id":"board_height","rule_name":"连板高度识别","stage":"BoardHeightDetection","actual_value":f"{board_count}板","operator":">=","threshold":"2板","status":"PASS","score":None,"max_score":None,"reason":f"本轮周期高度为{board_count}板","formula":"连续收盘涨停计数","inputs":{"cycle_start_date":str(getattr(row,"cycle_start_date",None)),"cycle_board_high":board_count},"evaluated_at":None}],"primary_reason":f"识别为{board_count}板首次断板","completed_at":None},
            {"stage_id":"strategy-router","stage_name":"StrategyRouter","status":"PASS","score":None,"max_score":None,"rules":[{"rule_id":"strategy_route","rule_name":"高度模型路由","stage":"StrategyRouter","actual_value":sub_strategy,"operator":"route","threshold":"2-3 / 4-5 / 6+","status":"PASS","score":None,"max_score":None,"reason":route_reason,"formula":"按连板高度路由","inputs":{"board_height":board_count,"height_group":height_group,"height_rank":height_rank,"market_highest":market_highest},"evaluated_at":None}],"primary_reason":route_reason,"completed_at":None},
            {"stage_id":"height-model","stage_name":sub_strategy,"status":"PASS","score":None,"max_score":100,"rules":[],"primary_reason":f"使用{sub_strategy}独立权重配置","completed_at":None},
            {"stage_id":"first-break","stage_name":"FirstBreak","status":"PASS","score":None,"max_score":15,"rules":[],"primary_reason":str(getattr(row,"break_quality","首次断板")),"completed_at":None},
            {"stage_id":"auction","stage_name":"Auction","status":"PASS" if has_auction else "NO_DATA","score":None,"max_score":20,"rules":[],"primary_reason":"竞价已采集" if has_auction else "竞价数据缺失","completed_at":None},
            {"stage_id":"intraday","stage_name":"IntradayConfirmation","status":"PASS" if has_minute else "NO_DATA","score":None,"max_score":None,"rules":[],"primary_reason":candidate["primary_reason"],"completed_at":None},
        ]
        decision={"trade_date":trade_date.isoformat(),"symbol":symbol,"name":name,"strategy_version":"v0.2.0-height-router","config_version":"height-models-v1","decision_id":f"{trade_date.strftime('%Y%m%d')}-{symbol}","run_id":f"live-{trade_date.strftime('%Y%m%d')}","final_status":status,"current_stage":"Intraday" if has_minute else "Auction","total_score":None,"max_score":100,"primary_reason":candidate["primary_reason"],"board_height":board_count,"height_group":height_group,"height_rank":height_rank,"market_highest":market_highest,"sub_strategy":sub_strategy,"model_route_reason":route_reason,"stages":stages,"signal":None,"order":None,"position":None}
        _write(public_dir / f"decision-{symbol}.json", decision)
    market_count = int(latest.symbol.nunique())
    newest_minute = str(minute_today.minute.max()) if not minute_today.empty else "—"
    baseline = load_market_auction_progress(data_dir)
    baseline_days = int(baseline.get("qualified_days", 0))
    target_days = int(baseline.get("target_days", 20))
    kpis = [["全市场股票", f"{market_count:,}", "Tushare真实日线"], ["可交易股票", f"{int(latest.is_trading.sum()):,}", "当日有行情"], ["竞价基线", f"{baseline_days}/{target_days}日", "覆盖率达80%才计入"], ["基础候选", str(len(pool)), "首次断板"], ["竞价候选", str(len(auction_symbols)), f"来源 {auction_sources}"], ["分钟已采集", str(len(minute_symbols)), f"最新 {newest_minute}"], ["实际买入", "—", "未接入交易"], ["当前持仓", "—", "未接入交易"], ["今日策略收益", "—", "未计算"]]
    funnel = [["全市场", market_count], ["基础候选", len(pool)], ["竞价有数据", len(auction_symbols)], ["分钟有数据", len(minute_symbols)]]
    now = datetime.now().astimezone()
    pool_updated = datetime.fromtimestamp(pool_path.stat().st_mtime).astimezone().isoformat() if pool_path.exists() else now.isoformat()
    if trade_date > now.date():
        progress = {"stage":"股票池已生成","latest":f"已筛选 {len(pool)} 只股票进入 {trade_date.isoformat()} 股票池","next":"等待下一交易日开盘及09:25集合竞价","updated_at":pool_updated,"status":"waiting"}
    elif auction_today.empty:
        progress = {"stage":"等待竞价","latest":f"今日股票池已就绪，共 {len(pool)} 只候选","next":"09:26采集集合竞价并进行承接检查","updated_at":pool_updated,"status":"waiting"}
    elif minute_today.empty:
        updated = str(auction_today.ingested_at.max()) if "ingested_at" in auction_today else now.isoformat()
        progress = {"stage":"竞价已完成","latest":f"已获取 {len(auction_symbols)}/{len(pool)} 只候选的集合竞价","next":"等待09:30盘中分钟监控","updated_at":updated,"status":"running"}
    elif now.time() <= time(10, 1):
        progress = {"stage":"盘中监控中","latest":f"已监控 {len(minute_symbols)}/{len(pool)} 只候选，最新分钟 {newest_minute}","next":"持续监控至10:01并检查盘中确认条件","updated_at":now.isoformat(),"status":"running"}
    elif now.time() < time(16, 10):
        progress = {"stage":"盘中监控已完成","latest":f"早盘监控完成，覆盖 {len(minute_symbols)}/{len(pool)} 只候选","next":"等待16:10收盘归档","updated_at":now.isoformat(),"status":"waiting"}
    else:
        progress = {"stage":"等待收盘处理","latest":f"当日行情已采集，覆盖 {len(minute_symbols)}/{len(pool)} 只候选","next":"归档后生成下一交易日股票池","updated_at":now.isoformat(),"status":"waiting"}
    _write(public_dir / "dashboard.json", {"progress": progress, "kpis": kpis, "funnel": funnel, "candidates": candidates})
    _write(public_dir / "candidates.json", candidates)
    _write(public_dir / "pipeline.json", pipeline)
    return {"pool": len(pool), "minute_symbols": len(minute_symbols), "auction_symbols": len(auction_symbols)}
