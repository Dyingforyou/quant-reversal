"""Publish real market observations and durable paper-account decisions."""
from datetime import date, datetime
from pathlib import Path
import json
import pandas as pd

from .market_auction_progress import load_market_auction_progress
from ..paper import clean, snapshot


def _write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(clean(value), ensure_ascii=False, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def publish_dashboard(data_dir: Path, public_dir: Path, trade_date: date) -> dict[str, int]:
    pool_path = data_dir / f"base_pool_{trade_date.strftime('%Y%m%d')}.csv"
    pool = pd.read_csv(pool_path, dtype={"symbol": str}) if pool_path.exists() else pd.DataFrame()
    daily = pd.read_parquet(data_dir / "daily_bars.parquet")
    minute_path = data_dir / "minute_bars.parquet"
    auction_path = data_dir / "auction.parquet"
    minute = pd.read_parquet(minute_path) if minute_path.exists() else pd.DataFrame()
    auction = pd.read_parquet(auction_path) if auction_path.exists() else pd.DataFrame()
    master = pd.read_parquet(data_dir / "security_master.parquet")
    names = dict(zip(master.symbol.astype(str), master.name.astype(str)))
    minute_today = minute[pd.to_datetime(minute.trade_date).dt.date == trade_date] if not minute.empty else minute
    auction_today = auction[pd.to_datetime(auction.trade_date).dt.date == trade_date] if not auction.empty else auction
    latest = daily[pd.to_datetime(daily.trade_date).dt.date == pd.to_datetime(daily.trade_date).dt.date.max()]
    pool_symbols = set(pool.symbol.astype(str).str.zfill(6)) if not pool.empty else set()
    minute_symbols = set(minute_today.symbol.astype(str)) if not minute_today.empty else set()
    auction_symbols = set(auction_today.symbol.astype(str)) & pool_symbols if not auction_today.empty else set()
    paper = snapshot(data_dir, trade_date)
    evaluated = {d["symbol"]: d for d in paper["decisions"]}
    candidates, pipeline = [], []
    now = datetime.now().astimezone()
    for row in pool.to_dict("records"):
        symbol = str(row["symbol"]).zfill(6)
        height = int(row.get("board_count", row.get("prev_streak_height", 0)))
        route = f"{height}板，路由至{row.get('sub_strategy','')}"
        decision = evaluated.get(symbol, {
            "trade_date": str(trade_date), "symbol": symbol, "name": names.get(symbol,symbol),
            "strategy_version":"v0.3.0-paper", "config_version":"real", "decision_id":f"{trade_date}-{symbol}",
            "run_id":f"paper-{trade_date}", "final_status":"WAITING", "current_stage":"等待策略评估",
            "total_score":None, "max_score":100, "primary_reason":"股票池已准备，等待交易日竞价与模拟策略评估",
            "board_height":height, "height_group":row.get("height_group",""), "height_rank":int(row.get("height_rank",0)),
            "market_highest":bool(row.get("is_market_highest",False)), "sub_strategy":row.get("sub_strategy",""),
            "model_route_reason":route, "stages":[], "signal":None,"order":None,"position":None,"grade":"—",
            "metrics":{}, "updated_at":now.isoformat()})
        metrics = decision.get("metrics",{})
        statuses = {s["stage_name"]:s["status"] for s in decision["stages"]}
        candidate = {"symbol":symbol,"name":decision["name"],"status":decision["final_status"],
                     "score":decision["total_score"],"grade":decision.get("grade","—"),
                     "board_count":height,"board_height":height,"height_group":decision["height_group"],
                     "height_rank":decision["height_rank"],"market_highest":decision["market_highest"],
                     "sub_strategy":decision["sub_strategy"],"sector_name":metrics.get("sector_name") or "暂无板块数据",
                     "sector_score":metrics.get("sector_score"),"ma5_distance":metrics.get("ma5_distance"),
                     "auction_score":metrics.get("auction_score"),"auction_volume_ratio":metrics.get("auction_volume_ratio"),
                     "intraday_status":statuses.get("IntradayConfirmation","NOT_RUN"),"primary_reason":decision["primary_reason"]}
        candidates.append(candidate)
        pipeline.append({"trade_date":str(trade_date), **{k:candidate[k] for k in ["symbol","name","board_height","height_group","height_rank","market_highest","sub_strategy"]},
                         "model_route_reason":decision["model_route_reason"],"final_status":decision["final_status"],
                         "current_stage":decision["current_stage"],"stage_statuses":statuses,"total_score":decision["total_score"],
                         "grade":candidate["grade"],"rejection_stage":next((s["stage_name"] for s in decision["stages"] if s["status"] in ["NO_DATA","FAIL"]),None),
                         "rejection_rule":None,"rejection_reason":decision["primary_reason"],"updated_at":decision["updated_at"]})
        _write(public_dir / f"decision-{symbol}.json", decision)
    for position in paper["positions"]:
        symbol = position["symbol"]
        if symbol not in pool_symbols:
            _write(public_dir / f"decision-{symbol}.json", {"trade_date":str(trade_date),"symbol":symbol,"name":position["name"],
                "strategy_version":"v0.3.0-paper","config_version":"real","decision_id":f"{trade_date}-{symbol}","run_id":f"paper-{trade_date}",
                "final_status":"OPEN","current_stage":"持仓管理","total_score":None,"max_score":100,"primary_reason":"已离开候选池，继续采集行情并按T+1管理持仓",
                "board_height":0,"height_group":"—","height_rank":0,"market_highest":False,"sub_strategy":"持仓管理","model_route_reason":"已有模拟持仓",
                "stages":[],"signal":None,"order":next((o for o in paper["orders"] if o["symbol"]==symbol),None),"position":position})
    baseline = load_market_auction_progress(data_dir)
    opening_path = data_dir / "opening_amounts.parquet"
    opening_days = pd.read_parquet(opening_path).trade_date.nunique() if opening_path.exists() else 0
    buys = sum(f["side"]=="BUY" and f["timestamp"].startswith(str(trade_date)) for f in paper["fills"])
    triggered = sum(d["signal"] is not None for d in paper["decisions"])
    newest = str(minute_today.minute.max()) if not minute_today.empty else "—"
    ret = paper.get("daily_return")
    kpis = [["全市场股票",f"{latest.symbol.nunique():,}","真实日线"],
            ["竞价基线",f"{baseline.get('qualified_days',0)}/20日","逐股检查20个历史交易日"],
            ["开盘5分钟积累",f"{opening_days}/20日","09:35全市场快照，逐股检查"],
            ["基础候选",str(len(pool)),"首次断板"],["竞价有数据",str(len(auction_symbols)),"数据存在不等于规则通过"],
            ["分钟已采集",str(len(minute_symbols)),f"最新 {newest}"],
            ["模拟买入",str(buys),"仅模拟成交"],["当前模拟持仓",str(len(paper['positions'])),"遵守T+1"],
            ["今日模拟收益",f"{ret:+.2%}" if ret is not None else "—","含费用及持仓浮盈"],
            ["模拟可用资金",f"{paper.get('cash',0):,.2f}" if paper['enabled'] else "—","人民币"],
            ["模拟总资产",f"{paper.get('total_assets',0):,.2f}" if paper['enabled'] else "—","现金+持仓市值"]]
    if trade_date > now.date():
        stage, message, next_step = "股票池已生成", f"已准备 {trade_date} 的 {len(pool)} 只候选", "下一交易日采集竞价并执行模拟策略"
    else:
        stage = "模拟策略已评估" if evaluated else "等待策略评估"
        reasons = sorted({d["primary_reason"] for d in paper["decisions"]})
        message = "；".join(reasons) if reasons else f"股票池 {len(pool)} 只，等待行情或无候选"
        next_step = "09:35自动积累全市场开盘成交额；达标后模拟买入，次日管理卖出"
    progress = {"stage":stage,"latest":message,"next":next_step,"updated_at":paper.get("checked_at") or now.isoformat(),"status":"waiting"}
    _write(public_dir/"dashboard.json", {"progress":progress,"kpis":kpis,
        "funnel":[["全市场",int(latest.symbol.nunique())],["基础候选",len(pool)],["竞价有数据",len(auction_symbols)],["策略已评分",sum(c['score'] is not None for c in candidates)],["盘中触发",triggered],["模拟买入",buys]],"candidates":candidates})
    _write(public_dir/"candidates.json", candidates)
    _write(public_dir/"pipeline.json", pipeline)
    _write(public_dir/"trading.json", {k:v for k,v in paper.items() if k!="decisions"})
    return {"pool":len(pool),"minute_symbols":len(minute_symbols),"auction_symbols":len(auction_symbols),"paper_buys":buys,"paper_positions":len(paper['positions'])}
