"""Durable, idempotent paper trading. Never submits an order to a broker."""
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import json
import math
import sqlite3

import pandas as pd

from .backtest.fill import try_fill
from .config import load_config
from .data.local import LocalParquetProvider
from .features.intraday import intraday_snapshots
from .models import Candidate, Order, Side
from .pipeline import candidates_for_date
from .strategy.triggers import is_intraday_confirmed


def clean(value):
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if hasattr(value, "item"):
        return clean(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def dumps(value):
    return json.dumps(clean(value), ensure_ascii=False, allow_nan=False)


def connect(root: Path):
    db = sqlite3.connect(root / "paper.sqlite3", timeout=30)
    db.row_factory = sqlite3.Row
    db.executescript("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS positions(symbol TEXT PRIMARY KEY, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY, day TEXT NOT NULL,
            symbol TEXT NOT NULL, side TEXT NOT NULL, state TEXT NOT NULL, payload TEXT NOT NULL,
            UNIQUE(day,symbol,side));
        CREATE TABLE IF NOT EXISTS fills(order_id INTEGER PRIMARY KEY, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS decisions(day TEXT NOT NULL, symbol TEXT NOT NULL,
            payload TEXT NOT NULL, PRIMARY KEY(day,symbol));
        CREATE TABLE IF NOT EXISTS equity(day TEXT PRIMARY KEY, opening REAL NOT NULL, total REAL NOT NULL);
    """)
    return db


def positions(root: Path) -> list[dict]:
    if not (root / "paper.sqlite3").exists():
        return []
    with connect(root) as db:
        return [json.loads(row[0]) for row in db.execute("SELECT payload FROM positions")]


def _read(root, name):
    path = root / f"{name}.parquet"
    return pd.read_parquet(path) if path.exists() else pd.DataFrame()


def _day(frame, day):
    return frame[pd.to_datetime(frame.trade_date).dt.date == day].copy() if not frame.empty else frame


def _stamp(day, minute):
    return datetime.fromisoformat(f"{day}T{minute}:00")


def _opening_history(root, minute, day, symbol, lookback):
    """Never mix a timed quote baseline with full-minute OHLCV observations."""
    quote = _read(root, "opening_amounts")
    if not quote.empty:
        quote = quote[quote.symbol.astype(str) == symbol].sort_values("trade_date")
        prior = quote[pd.to_datetime(quote.trade_date).dt.date < day].tail(lookback)
        current = _day(quote, day)
        if not current.empty:
            return prior.amount, float(current.iloc[-1].amount), str(current.iloc[-1].observed_at), "定时行情快照"
    prior = minute[(minute.symbol.astype(str) == symbol) & (pd.to_datetime(minute.trade_date).dt.date < day)] if not minute.empty else minute
    rows = []
    if not prior.empty:
        for _, group in prior.groupby("trade_date"):
            opening = group[group.minute.astype(str).between("09:31", "09:35")]
            if set(opening.minute.astype(str)) == {"09:31", "09:32", "09:33", "09:34", "09:35"} and (opening.quality == "full_ohlcv").all():
                rows.append((group.trade_date.iloc[0], float(opening.amount.sum())))
    history = pd.Series([a for _, a in sorted(rows)[-lookback:]], dtype=float)
    return history, None, None, "完整分钟线"


def _candidates(root, cfg, day):
    """Scoring uses prior daily data and current auction; cache per input revision."""
    fingerprint = [str(day), cfg.model_dump(mode="json")]
    for name in ["daily_bars", "auction", "sector_membership"]:
        path = root / f"{name}.parquet"
        fingerprint.append(path.stat().st_mtime_ns if path.exists() else None)
    cache = root / f"paper_candidates_{day.strftime('%Y%m%d')}.json"
    key = dumps(fingerprint)
    if cache.exists():
        value = json.loads(cache.read_text())
        if value["key"] == key:
            return [Candidate.model_validate(c) for c in value["candidates"]]
    result = candidates_for_date(LocalParquetProvider(root), day, cfg)
    value = {"key": key, "candidates": [c.model_dump(mode="json") for c in result]}
    temporary = cache.with_suffix(".tmp")
    temporary.write_text(dumps(value), encoding="utf-8")
    temporary.replace(cache)
    return result


def _stage(name, status, reason, actual=None, threshold=None, score=None, maximum=None):
    return {"stage_id": name.lower(), "stage_name": name, "status": status,
            "score": score, "max_score": maximum, "primary_reason": reason, "completed_at": None,
            "rules": [{"rule_id": name.lower(), "rule_name": name, "stage": name,
                       "actual_value": str(actual) if actual is not None else None,
                       "operator": ">=", "threshold": str(threshold) if threshold is not None else None,
                       "status": status, "score": score, "max_score": maximum, "reason": reason,
                       "formula": None, "inputs": None, "evaluated_at": None}]}


def evaluate(root: Path, config: Path, day: date, now: datetime | None = None) -> dict:
    cfg = load_config(config)
    now = now or datetime.now(ZoneInfo(cfg.project.timezone)).replace(tzinfo=None)
    if now.tzinfo:
        now = now.astimezone(ZoneInfo(cfg.project.timezone)).replace(tzinfo=None)
    if day != now.date():
        raise ValueError("模拟交易只处理当前交易日，禁止回填历史买卖")
    calendar = _read(root, "trading_calendar")
    today_calendar = _day(calendar, day)
    if today_calendar.empty or not bool(today_calendar.iloc[-1].is_open):
        return {"status": "closed", "reason": "交易日历未确认今日开市"}
    minute = _read(root, "minute_bars")
    bars = _day(minute, day)
    if not bars.empty:
        bars = bars[bars.minute.astype(str) < now.strftime("%H:%M")].sort_values("minute")
    daily = _read(root, "daily_bars")
    prior = daily[pd.to_datetime(daily.trade_date).dt.date < day]
    auction = _day(_read(root, "auction"), day)
    limits = _day(_read(root, "price_limits"), day)
    pool_path = root / f"base_pool_{day.strftime('%Y%m%d')}.csv"
    pool = pd.read_csv(pool_path, dtype={"symbol": str}) if pool_path.exists() else pd.DataFrame()
    names_frame = _read(root, "security_master")
    names = dict(zip(names_frame.symbol.astype(str), names_frame.name)) if not names_frame.empty else {}
    error = None
    try:
        candidates = _candidates(root, cfg, day) if not pool.empty and not auction.empty else []
    except (FileNotFoundError, KeyError, ValueError) as exc:
        candidates = []
        error = f"策略依赖数据缺失：{exc}"
    by_symbol = {c.symbol: c for c in candidates}
    db = connect(root)
    try:
        db.execute("BEGIN IMMEDIATE")
        for key, value in [("cash", cfg.backtest.initial_cash), ("initial_cash", cfg.backtest.initial_cash), ("activated_at", now.isoformat())]:
            db.execute("INSERT OR IGNORE INTO meta VALUES (?,?)", (key, str(value)))
        cash = float(db.execute("SELECT value FROM meta WHERE key='cash'").fetchone()[0])
        activated = datetime.fromisoformat(db.execute("SELECT value FROM meta WHERE key='activated_at'").fetchone()[0])
        held = {row["symbol"]: json.loads(row["payload"]) for row in db.execute("SELECT * FROM positions")}

        # Fill previously signalled orders before considering any new signals.
        for record in db.execute("SELECT * FROM orders WHERE state='PENDING'").fetchall():
            order = Order.model_validate(json.loads(record["payload"]))
            if record["day"] != day.isoformat():
                db.execute("UPDATE orders SET state='EXPIRED' WHERE id=?", (record["id"],))
                continue
            sb = bars[bars.symbol.astype(str) == order.symbol] if not bars.empty else bars
            allowed = sb[sb.minute.astype(str) >= order.earliest_fill_at.strftime("%H:%M")] if not sb.empty else sb
            if allowed.empty:
                continue
            bar = allowed.iloc[-1] if order.side == Side.SELL else allowed.iloc[0]
            if now - _stamp(day, bar.minute) > timedelta(minutes=3):
                if order.side == Side.BUY:
                    db.execute("UPDATE orders SET state='EXPIRED' WHERE id=?", (record["id"],))
                continue
            price_limit = limits[limits.symbol.astype(str) == order.symbol] if not limits.empty else limits
            if price_limit.empty or bar.get("quality") != "full_ohlcv":
                continue
            limit = price_limit.iloc[-1]
            if not math.isfinite(float(limit.limit_up_price)) or not math.isfinite(float(limit.limit_down_price)):
                continue
            fill = try_fill(order, bar, float(limit.limit_up_price), float(limit.limit_down_price),
                            cfg.entry.slippage_bps, cfg.costs.commission_bps,
                            cfg.costs.min_commission, cfg.costs.sell_tax_bps)
            if fill is None:
                continue
            value = fill.price * fill.quantity
            if order.side == Side.BUY:
                if value + fill.commission > cash or len(held) >= cfg.backtest.max_positions or order.symbol in held:
                    db.execute("UPDATE orders SET state='REJECTED' WHERE id=?", (record["id"],))
                    continue
                cash -= value + fill.commission
                position = {"symbol": order.symbol, "name": names.get(order.symbol, order.symbol),
                            "quantity": fill.quantity, "entry_price": fill.price,
                            "entry_date": str(day), "entry_time": fill.timestamp.isoformat(),
                            "entry_cost": fill.commission}
                held[order.symbol] = position
                db.execute("INSERT INTO positions VALUES (?,?)", (order.symbol, dumps(position)))
            else:
                position = held.get(order.symbol)
                if not position or position["entry_date"] >= str(day):
                    continue  # T+1, regardless of strategy/config switches.
                cash += value - fill.commission - fill.tax
                del held[order.symbol]
                db.execute("DELETE FROM positions WHERE symbol=?", (order.symbol,))
            db.execute("INSERT INTO fills VALUES (?,?)", (record["id"], dumps(fill.model_dump(mode="json"))))
            db.execute("UPDATE orders SET state='FILLED' WHERE id=?", (record["id"],))

        # Manage held symbols even after they leave the next day's candidate pool.
        for symbol, position in held.items():
            sb = bars[bars.symbol.astype(str) == symbol] if not bars.empty else bars
            if position["entry_date"] >= str(day) or sb.empty:
                continue
            bar = sb.iloc[-1]
            timestamp = _stamp(day, bar.minute)
            if now - timestamp > timedelta(minutes=3):
                continue
            reason = None
            if cfg.exit.base_mode == "next_day_1000" and str(bar.minute) >= "10:00":
                reason = "T+1 10:00退出"
            elif cfg.exit.base_mode == "stop" and bar.close / position["entry_price"] - 1 <= cfg.exit.fixed_stop_pct:
                reason = "达到止损线"
            elif cfg.exit.base_mode == "take_profit" and bar.close / position["entry_price"] - 1 >= cfg.exit.take_profit_pct:
                reason = "达到止盈线"
            elif cfg.exit.base_mode == "max_holding":
                elapsed = calendar[(pd.to_datetime(calendar.trade_date).dt.date > date.fromisoformat(position["entry_date"])) & (pd.to_datetime(calendar.trade_date).dt.date <= day) & calendar.is_open]
                if len(elapsed) >= cfg.exit.max_holding_days:
                    reason = "达到最大持有交易日"
            if reason:
                order = Order(symbol=symbol, side=Side.SELL, quantity=position["quantity"], created_at=timestamp,
                              earliest_fill_at=timestamp + timedelta(minutes=1), reason=reason)
                db.execute("INSERT OR IGNORE INTO orders(day,symbol,side,state,payload) VALUES (?,?,?,'PENDING',?)", (str(day), symbol, "SELL", dumps(order.model_dump(mode="json"))))

        decisions = []
        pending_cash = 0.0
        for record in db.execute("SELECT payload FROM orders WHERE side='BUY' AND state='PENDING'"):
            order = json.loads(record[0]); sb = bars[bars.symbol.astype(str) == order["symbol"]] if not bars.empty else bars
            if not sb.empty:
                pending_cash += order["quantity"] * float(sb.iloc[-1].close) * 1.01 + cfg.costs.min_commission
        records = list(pool.to_dict("records")) if not pool.empty else []
        records.sort(key=lambda row: (-by_symbol[row["symbol"]].total_score if row["symbol"] in by_symbol else 0, row["symbol"]))
        for row in records:
            symbol = str(row["symbol"]).zfill(6)
            c = by_symbol.get(symbol)
            stages = []
            status, reason = "NO_DATA", error or "缺少当日竞价或策略输入"
            history, quote_current, available, measurement = _opening_history(root, minute, day, symbol, cfg.auction.lookback)
            ratio = None
            sb = bars[bars.symbol.astype(str) == symbol] if not bars.empty else bars
            stages.append(_stage("Sector", "PASS" if c and c.best_sector_id else "NO_DATA", "真实行业快照" if c and c.best_sector_id else "缺少有效板块数据", score=c.sector_score if c else None, maximum=20))
            if c:
                stages.append(_stage(c.sub_strategy, "PASS" if c.total_score >= cfg.score.grade_b else "FAIL", f"总分 {c.total_score:.2f}，买入门槛 {cfg.score.grade_b}", c.total_score, cfg.score.grade_b, c.total_score, 100))
                for name, score, maximum in [("FirstBreak",c.break_score,15),("MA5",c.ma5_score,15),("Auction",c.auction_score,20)]:
                    stages.append(_stage(name, "PASS", f"{name}实际得分 {score:.2f}", score=score, maximum=maximum))
                ah = _read(root, "auction")
                ah = ah[(ah.symbol.astype(str)==symbol) & (pd.to_datetime(ah.trade_date).dt.date<day)]
                auction_days = len(ah)
                stages.append(_stage("AuctionBaseline", "PASS" if auction_days>=cfg.auction.lookback else "NO_DATA", f"该股历史竞价 {auction_days}/{cfg.auction.lookback}日", auction_days, cfg.auction.lookback))
                stages.append(_stage("OpeningBaseline", "PASS" if len(history)>=cfg.auction.lookback else "NO_DATA", f"开盘5分钟基线 {len(history)}/{cfg.auction.lookback}日（{measurement}）", len(history), cfg.auction.lookback))
                if not c.best_sector_id:
                    reason = "该股缺少有效板块成员数据"
                elif auction_days < cfg.auction.lookback:
                    reason = f"该股历史竞价不足：{auction_days}/{cfg.auction.lookback}日"
                elif c.total_score < cfg.score.grade_b:
                    status, reason = "REJECT", f"评分 {c.total_score:.2f} < 开仓门槛 {cfg.score.grade_b}"
                elif len(history) < cfg.auction.lookback or history.median() <= 0:
                    reason = f"开盘5分钟成交额历史不足：{len(history)}/{cfg.auction.lookback}日（{measurement}）"
                elif sb.empty or now - _stamp(day, sb.iloc[-1].minute) > timedelta(minutes=3):
                    status, reason = "WAITING", "行情未到或超过3分钟，停止新开仓"
                else:
                    ac = auction[auction.symbol.astype(str) == symbol].iloc[-1]
                    pc = float(prior[prior.symbol.astype(str) == symbol].sort_values("trade_date").iloc[-1].close)
                    snap = intraday_snapshots(sb, pc, c.ma5_ref, float(ac.auction_price), history)
                    if snap.empty:
                        status, reason = "WATCH", "当前不在早盘开仓窗口"
                    else:
                        current = snap.iloc[-1].copy()
                        current["running_low"] = float(snap.low.min())
                        if quote_current is not None:
                            current["open5m_volume_ratio20"] = quote_current / history.median() if available and datetime.fromisoformat(available).replace(tzinfo=None) <= _stamp(day, current.minute) else float("nan")
                        ratio = current.open5m_volume_ratio20
                        confirmed = is_intraday_confirmed(current, c.total_score, pc, c.ma5_ref, float(ac.auction_price), cfg.intraday.open5m_volume_ratio_min, cfg.intraday.max_rebreak_ma5_count, cfg.score.grade_b)
                        if cfg.intraday.require_reclaim_prev_close:
                            confirmed = confirmed and current.close >= pc
                        stages.append(_stage("IntradayConfirmation", "PASS" if confirmed else "FAIL", f"站回MA5、量比≥{cfg.intraday.open5m_volume_ratio_min}、反包价格确认", ratio, cfg.intraday.open5m_volume_ratio_min))
                        timestamp = _stamp(day, current.minute)
                        has_limits = not limits.empty and symbol in set(limits.symbol.astype(str))
                        pending_count = db.execute("SELECT COUNT(*) FROM orders WHERE state='PENDING' AND side='BUY'").fetchone()[0]
                        if timestamp < activated or timestamp.strftime("%H:%M") > cfg.intraday.max_entry_time or now > _stamp(day, cfg.intraday.max_entry_time) + timedelta(minutes=1):
                            status, reason = "WATCH", "开仓窗口已结束或行情早于账户启用时间，不补历史买入"
                        elif not has_limits:
                            reason = "缺少当日真实涨跌停价"
                        elif current.get("quality") != "full_ohlcv":
                            reason = "仅有分钟收盘价，缺少真实OHLC，停止模拟成交"
                        elif not confirmed:
                            status, reason = "WATCH", "盘中确认条件未满足"
                        elif len(held) + pending_count >= cfg.backtest.max_positions:
                            status, reason = "WATCH", "持仓及待成交订单已达上限"
                        elif symbol in held:
                            status, reason = "OPEN", "该股已持仓"
                        else:
                            budget = min(cash - pending_cash, cfg.backtest.initial_cash * cfg.backtest.position_size_pct)
                            price = float(current.close) * (1 + cfg.entry.slippage_bps/10000)
                            lot = cfg.backtest.lot_size
                            quantity = max(0, int((budget-cfg.costs.min_commission)/(price*(1+cfg.costs.commission_bps/10000))/lot)*lot)
                            if quantity:
                                order = Order(symbol=symbol, side=Side.BUY, quantity=quantity, created_at=timestamp,
                                              earliest_fill_at=timestamp+timedelta(minutes=1), reason="评分达标且盘中确认")
                                inserted = db.execute("INSERT OR IGNORE INTO orders(day,symbol,side,state,payload) VALUES (?,?,?,'PENDING',?)", (str(day), symbol, "BUY", dumps(order.model_dump(mode="json")))).rowcount
                                if inserted:
                                    pending_cash += quantity * price * 1.01 + cfg.costs.min_commission
                                status, reason = "TRIGGERED", "买入信号已记录，等待下一分钟真实开盘价模拟成交"
                            else:
                                status, reason = "REJECT", "可用资金不足一手及手续费"
            order_row = db.execute("SELECT * FROM orders WHERE day=? AND symbol=? AND side='BUY'", (str(day),symbol)).fetchone()
            order_payload = dict(json.loads(order_row["payload"]), state=order_row["state"]) if order_row else None
            if symbol in held:
                status, reason = "OPEN", "模拟买入已成交，遵守T+1管理持仓"
            elif order_row:
                status = {"FILLED":"FILLED", "PENDING":"TRIGGERED", "EXPIRED":"WATCH", "REJECTED":"REJECT"}[order_row["state"]]
                reason = {"FILLED":"模拟买入已成交", "PENDING":"等待下一分钟模拟成交", "EXPIRED":"订单行情超过3分钟或跨日，已失效", "REJECTED":"资金或持仓上限拒绝成交"}[order_row["state"]]
            decision = {"trade_date": str(day), "symbol": symbol, "name": names.get(symbol,symbol),
                        "strategy_version": "v0.3.0-paper", "config_version": "real",
                        "decision_id": f"{day}-{symbol}", "run_id": f"paper-{day}",
                        "final_status":status, "current_stage": "PaperTrading", "total_score": c.total_score if c else None,
                        "max_score":100, "primary_reason":reason, "board_height":int(row.get("board_count",0)),
                        "height_group":row.get("height_group",""), "height_rank":int(row.get("height_rank",0)),
                        "market_highest":bool(row.get("is_market_highest",False)), "sub_strategy":row.get("sub_strategy",""),
                        "model_route_reason":c.model_route_reason if c else "按首次断板高度路由", "stages":stages,
                        "signal": {"timestamp":order_payload["created_at"],"type":"ENTRY_TRIGGER"} if order_payload else None,
                        "order":order_payload,"position":held.get(symbol), "grade":c.grade if c else "—",
                        "metrics":{"sector_score":c.sector_score if c else None,"sector_name":c.best_sector_id if c else None,
                                   "auction_score":c.auction_score if c else None,"auction_volume_ratio":c.raw_features.get("auction_volume_ratio20") if c else None,
                                   "ma5_distance":c.ma5_distance_auction if c else None,"open5_history_days":len(history),"open5_volume_ratio":ratio},
                        "updated_at":now.isoformat()}
            decision = clean(decision)
            db.execute("INSERT OR REPLACE INTO decisions VALUES (?,?,?)", (str(day),symbol,dumps(decision)))
            decisions.append(decision)
        db.execute("UPDATE meta SET value=? WHERE key='cash'", (str(cash),))
        total = cash
        for symbol, position in held.items():
            sb = bars[bars.symbol.astype(str) == symbol] if not bars.empty else bars
            mark = float(sb.iloc[-1].close) if not sb.empty else position["entry_price"]
            position["last_price"] = mark
            position["market_value"] = mark * position["quantity"]
            position["unrealized_pnl"] = (mark-position["entry_price"])*position["quantity"] - position["entry_cost"]
            total += position["market_value"]
            db.execute("UPDATE positions SET payload=? WHERE symbol=?", (dumps(position),symbol))
        previous = db.execute("SELECT total FROM equity WHERE day<? ORDER BY day DESC LIMIT 1", (str(day),)).fetchone()
        initial = float(db.execute("SELECT value FROM meta WHERE key='initial_cash'").fetchone()[0])
        db.execute("INSERT INTO equity VALUES (?,?,?) ON CONFLICT(day) DO UPDATE SET total=excluded.total", (str(day),previous[0] if previous else initial,total))
        db.execute("INSERT OR REPLACE INTO meta VALUES ('checked_at',?)", (now.isoformat(),))
        db.commit()
        return {"status":"ok", "candidates":len(decisions), "positions":len(held), "cash":cash,
                "total_assets":total, "blocked":sum(d['final_status']=='NO_DATA' for d in decisions)}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def snapshot(root: Path, day: date) -> dict:
    if not (root / "paper.sqlite3").exists():
        return {"enabled":False, "decisions":[], "positions":[], "orders":[], "fills":[]}
    with connect(root) as db:
        meta = dict(db.execute("SELECT key,value FROM meta").fetchall())
        orders = [dict(json.loads(row["payload"]), id=row["id"], state=row["state"]) for row in db.execute("SELECT * FROM orders ORDER BY id DESC")]
        fills = [dict(json.loads(row["payload"]), order_id=row["order_id"]) for row in db.execute("SELECT * FROM fills ORDER BY order_id DESC")]
        equity = db.execute("SELECT * FROM equity WHERE day=?",(str(day),)).fetchone()
        return {"enabled":True,"mode":"paper", "activated_at":meta.get("activated_at"), "checked_at":meta.get("checked_at"),
                "cash":float(meta.get("cash",0)), "total_assets":equity["total"] if equity else float(meta.get("cash",0)),
                "daily_return":(equity["total"]/equity["opening"]-1) if equity and equity["opening"] else None,
                "decisions":[json.loads(row[0]) for row in db.execute("SELECT payload FROM decisions WHERE day=?",(str(day),))],
                "positions":[json.loads(row[0]) for row in db.execute("SELECT payload FROM positions")],
                "orders":orders,"fills":fills}
