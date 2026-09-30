"""Command line interface."""
from datetime import date
from pathlib import Path
import json
import pandas as pd
import typer
from rich.console import Console
from .backtest.engine import run_backtest
from .config import load_config
from .data.local import LocalParquetProvider
from .data.validation import validate_directory
from .data.store import ParquetStore
from .data.collector import base_pool, collect_auction, collect_daily, collect_intraday
from .fixtures import generate
from .pipeline import candidates_for_date
from .research.buckets import bucket_stats
from .research.report import write_html
from .research.samples import build_samples
from .run import create_run
from .scan.report import write_scan
app=typer.Typer(help="量化反包研究、回测与选股工具");data_app=typer.Typer();research_app=typer.Typer();backtest_app=typer.Typer();scan_app=typer.Typer();paper_app=typer.Typer()
app.add_typer(data_app,name="data");app.add_typer(research_app,name="research");app.add_typer(backtest_app,name="backtest");app.add_typer(scan_app,name="scan");console=Console()
app.add_typer(paper_app,name="paper")

@paper_app.command("run")
def paper_run(date_:str=typer.Option(...,"--date"),config:Path=typer.Option(Path("configs/real.yaml"))):
    from .paper import evaluate
    cfg=load_config(config)
    console.print_json(data=evaluate(cfg.project.data_dir,config,date.fromisoformat(date_)))

@data_app.command("is-trading-day")
def data_is_trading_day(date_:str=typer.Option(...,"--date"),output:Path=typer.Option(Path("data/normalized"))):
    path=output/"trading_calendar.parquet"
    if not path.exists(): raise typer.Exit(1)
    calendar=pd.read_parquet(path)
    selected=calendar[pd.to_datetime(calendar.trade_date).dt.date==date.fromisoformat(date_)]
    if selected.empty or not selected.is_open.any(): raise typer.Exit(1)

@data_app.command("collect-reference")
def data_collect_reference(date_:str=typer.Option(...,"--date"),token:str=typer.Option("",envvar="TUSHARE_TOKEN"),output:Path=typer.Option(Path("data/normalized"))):
    from .data.trading_reference import collect_reference
    from .data.tushare_source import TushareDailySource
    if not token: raise typer.BadParameter("请通过 TUSHARE_TOKEN 提供令牌")
    console.print_json(data=collect_reference(TushareDailySource(token),output,date.fromisoformat(date_)))

@data_app.command("collect-opening")
def data_collect_opening(date_:str=typer.Option(...,"--date"),output:Path=typer.Option(Path("data/normalized"))):
    from .data.tencent_market_auction import TencentMarketAuctionSource
    day=date.fromisoformat(date_)
    master=pd.read_parquet(output/"security_master.parquet")
    auction=pd.read_parquet(output/"auction.parquet")
    auction=auction[pd.to_datetime(auction.trade_date).dt.date==day]
    frame=TencentMarketAuctionSource().opening_amounts(day,master.symbol.astype(str).tolist(),auction)
    rows=ParquetStore(output).upsert("opening_amounts",frame,["trade_date","symbol"])
    console.print_json(data={"opening_amounts":rows,"universe":len(master),"source":"tencent_open5_quote"})
    if rows==0: raise RuntimeError("开盘5分钟快照未取得数据")
def context(config):
    cfg=load_config(config)
    if not (cfg.project.data_dir/"daily_bars.parquet").exists():
        if cfg.project.data_dir.name != "fixtures":
            raise FileNotFoundError(f"真实数据目录尚未初始化：{cfg.project.data_dir}；请先执行 data collect-daily")
        generate(cfg.project.data_dir)
    return cfg,LocalParquetProvider(cfg.project.data_dir)
@data_app.command("validate")
def data_validate(config:Path=typer.Option(Path("configs/default.yaml")),log_level:str=typer.Option("INFO")):
    cfg,_=context(config);console.print_json(data=validate_directory(cfg.project.data_dir))

@data_app.command("collect-daily")
def data_collect_daily(start:str=typer.Option(...),end:str=typer.Option(...),symbols:str=typer.Option(...,help="逗号分隔的股票代码"),token:str=typer.Option("",envvar="TUSHARE_TOKEN"),output:Path=typer.Option(Path("data/normalized"))):
    """使用 Tushare 采集交易日历、日线和涨跌停价格。"""
    if not token: raise typer.BadParameter("请通过 --token 或 TUSHARE_TOKEN 提供令牌")
    from .data.tushare_source import TushareDailySource
    result=collect_daily(TushareDailySource(token),ParquetStore(output),date.fromisoformat(start),date.fromisoformat(end),[x.strip() for x in symbols.split(",") if x.strip()]);console.print_json(data=result)

@data_app.command("collect-intraday")
def data_collect_intraday(date_:str=typer.Option(...,"--date"),symbols:str=typer.Option(...,help="逗号分隔的股票代码"),output:Path=typer.Option(Path("data/normalized")),auction:bool=typer.Option(True,"--auction/--no-auction")):
    """使用 AKShare 采集近期一分钟线及独立 09:25 竞价快照。"""
    from .data.akshare_source import AkshareIntradaySource
    result=collect_intraday(AkshareIntradaySource(),ParquetStore(output),date.fromisoformat(date_),[x.strip() for x in symbols.split(",") if x.strip()],auction);console.print_json(data=result)

@data_app.command("collect-market")
def data_collect_market(date_:str=typer.Option(...,"--date"),lookback_days:int=typer.Option(45),token:str=typer.Option("",envvar="TUSHARE_TOKEN"),output:Path=typer.Option(Path("data/normalized"))):
    """拉取全市场日线，自动筛基础股票池，再采集候选的分钟与竞价。"""
    if not token: raise typer.BadParameter("请通过 TUSHARE_TOKEN 提供令牌")
    from datetime import timedelta
    from .data.tushare_source import TushareDailySource
    from .data.akshare_source import AkshareIntradaySource
    signal_date=date.fromisoformat(date_);store=ParquetStore(output);daily_source=TushareDailySource(token)
    daily_result=collect_daily(daily_source,store,signal_date-timedelta(days=lookback_days*2),signal_date,None)
    pool=base_pool(store,signal_date);pool_path=output/f"base_pool_{date_.replace('-', '')}.csv";pool.to_csv(pool_path,index=False)
    symbols=pool.symbol.astype(str).tolist() if not pool.empty else []
    intraday_result=collect_intraday(AkshareIntradaySource(),store,signal_date,symbols,True) if symbols else {"minute_bars":0,"auction":0}
    console.print_json(data={**daily_result,**intraday_result,"base_pool":len(pool)});console.print(pool_path)

def _pool_symbols(output:Path,date_:str)->list[str]:
    path=output/f"base_pool_{date_.replace('-', '')}.csv"
    if not path.exists(): raise FileNotFoundError(f"基础股票池不存在：{path}")
    frame=pd.read_csv(path,dtype={"symbol":str});return frame.symbol.astype(str).str.zfill(6).tolist()

def _free_intraday_source(auction:bool=False):
    from .data.akshare_source import AkshareIntradaySource
    from .data.fallback_source import FallbackIntradaySource
    from .data.tencent_source import TencentIntradaySource
    from .data.sina_source import SinaIntradaySource
    from .data.eastmoney_tick_source import EastmoneyTickAuctionSource
    sources=[AkshareIntradaySource(),TencentIntradaySource(),EastmoneyTickAuctionSource()] if auction else [SinaIntradaySource(),TencentIntradaySource(),AkshareIntradaySource()]
    return FallbackIntradaySource(sources)

@data_app.command("prepare-pool")
def data_prepare_pool(signal_date:str=typer.Option(...,"--date"),lookback_days:int=typer.Option(45),token:str=typer.Option("",envvar="TUSHARE_TOKEN"),output:Path=typer.Option(Path("data/normalized"))):
    """收盘后更新日线，并为下一交易日生成基础股票池。"""
    if not token: raise typer.BadParameter("请通过 TUSHARE_TOKEN 提供令牌")
    from datetime import timedelta
    from .data.tushare_source import TushareDailySource
    target=date.fromisoformat(signal_date);store=ParquetStore(output);source=TushareDailySource(token)
    result=collect_daily(source,store,target-timedelta(days=lookback_days*2),target-timedelta(days=1),None)
    pool=base_pool(store,target);path=output/f"base_pool_{signal_date.replace('-', '')}.csv";pool.to_csv(path,index=False)
    console.print_json(data={**result,"base_pool":len(pool)});console.print(path)

@data_app.command("prepare-next-pool")
def data_prepare_next_pool(trade_date:str=typer.Option(...,"--date"),token:str=typer.Option("",envvar="TUSHARE_TOKEN"),output:Path=typer.Option(Path("data/normalized"))):
    """在收盘后更新当日日线，并为下一个交易日生成基础股票池。"""
    if not token: raise typer.BadParameter("请通过 TUSHARE_TOKEN 提供令牌")
    from datetime import timedelta
    from .data.tushare_source import TushareDailySource
    today=date.fromisoformat(trade_date);store=ParquetStore(output);source=TushareDailySource(token)
    future=source.calendar(today+timedelta(days=1),today+timedelta(days=14))
    store.upsert("trading_calendar",future,["trade_date"])
    opens=future.loc[future.is_open,"trade_date"].tolist()
    if not opens: raise RuntimeError("未来14天内没有找到下一交易日")
    signal_date=opens[0]
    start=today if (output/"daily_bars.parquet").exists() else today-timedelta(days=90)
    result=collect_daily(source,store,start,today,None)
    pool=base_pool(store,signal_date);path=output/f"base_pool_{signal_date.strftime('%Y%m%d')}.csv";pool.to_csv(path,index=False)
    (output/"current_pool_date.txt").write_text(signal_date.isoformat(),encoding="utf-8")
    console.print_json(data={**result,"signal_date":signal_date.isoformat(),"base_pool":len(pool)});console.print(path)

@data_app.command("rebuild-pool")
def data_rebuild_pool(trade_date:str=typer.Option(...,"--date"),output:Path=typer.Option(Path("data/normalized")),min_board:int=typer.Option(2),max_board:int=typer.Option(10)):
    """不重新下载行情，使用本地真实日线按当前研究范围重建股票池。"""
    target=date.fromisoformat(trade_date);pool=base_pool(ParquetStore(output),target,min_board,max_board);path=output/f"base_pool_{target.strftime('%Y%m%d')}.csv";pool.to_csv(path,index=False);console.print_json(data={"signal_date":target.isoformat(),"research_pool":len(pool),"min_board":min_board,"max_board":max_board});console.print(path)

@data_app.command("collect-auction")
def data_collect_auction(date_:str=typer.Option(...,"--date"),output:Path=typer.Option(Path("data/normalized"))):
    """09:25 后为当日基础池采集独立集合竞价快照。"""
    symbols=_pool_symbols(output,date_);result=collect_auction(_free_intraday_source(True),ParquetStore(output),date.fromisoformat(date_),symbols);console.print_json(data={**result,"pool_size":len(symbols)})

@data_app.command("collect-market-auction")
def data_collect_market_auction(date_:str=typer.Option(...,"--date"),output:Path=typer.Option(Path("data/normalized"))):
    """09:25后批量保存全市场竞价快照，用于积累20日基线。"""
    from .data.market_auction_progress import record_market_auction_progress
    from .data.tencent_market_auction import TencentMarketAuctionSource
    master=pd.read_parquet(output/"security_master.parquet");symbols=master.symbol.astype(str).tolist();trade_date=date.fromisoformat(date_)
    frame=TencentMarketAuctionSource().snapshot(trade_date,symbols);rows=ParquetStore(output).upsert("auction",frame,["trade_date","symbol"])
    coverage=rows/len(symbols) if symbols else 0;progress=record_market_auction_progress(output,trade_date,rows,len(symbols));console.print_json(data={"market_auction":rows,"universe":len(symbols),"coverage":coverage,"baseline_days":progress["qualified_days"],"target_days":progress["target_days"]})
    if coverage<0.8: raise RuntimeError(f"全市场竞价覆盖率过低：{coverage:.1%}")

@data_app.command("collect-live-minute")
def data_collect_live_minute(date_:str=typer.Option(...,"--date"),output:Path=typer.Option(Path("data/normalized"))):
    """盘中为当日基础池增量采集一分钟行情。"""
    from .data.health import record_intraday_health
    from .paper import positions
    trade_date=date.fromisoformat(date_);symbols=sorted(set(_pool_symbols(output,date_))|{p["symbol"] for p in positions(output)});result=collect_intraday(_free_intraday_source(False),ParquetStore(output),trade_date,symbols,False);health=record_intraday_health(output,trade_date,symbols);console.print_json(data={**result,"pool_size":len(symbols),"health":health["status"],"stale_symbols":health["stale_symbols"]})

@data_app.command("publish-dashboard")
def data_publish_dashboard(date_:str=typer.Option(...,"--date"),output:Path=typer.Option(Path("data/normalized")),public:Path=typer.Option(Path("/var/www/html/quant-reversal/data"))):
    """把已落库的真实数据发布为看板静态 JSON。"""
    from .data.dashboard_export import publish_dashboard
    console.print_json(data=publish_dashboard(output,public,date.fromisoformat(date_)))
@research_app.command("build-samples")
def research_build(start:str=typer.Option(...),end:str=typer.Option(...),config:Path=typer.Option(Path("configs/research.yaml")),log_level:str=typer.Option("INFO")):
    start_date=date.fromisoformat(start);end_date=date.fromisoformat(end);cfg,p=context(config);root=create_run(cfg.project.output_dir,"research",cfg.model_dump(mode="json"),[start,end]);frame=build_samples(p,cfg,start_date,end_date);frame.to_parquet(root/"samples.parquet",index=False);frame.to_csv(root/"samples.csv",index=False);console.print(f"样本 {len(frame)} 条：{root}")
@research_app.command("bucket")
def research_bucket(factor:str=typer.Option(...),bins:str=typer.Option(...),samples:Path=typer.Option(...),config:Path=typer.Option(Path("configs/research.yaml")),log_level:str=typer.Option("INFO")):
    frame=pd.read_parquet(samples) if samples.suffix==".parquet" else pd.read_csv(samples);out=bucket_stats(frame,factor,[float(x) for x in bins.split(",")]);path=samples.parent/f"bucket_{factor}.csv";out.to_csv(path,index=False);console.print(out);console.print(path)
@research_app.command("report")
def research_report(samples:Path=typer.Option(...),config:Path=typer.Option(Path("configs/research.yaml")),log_level:str=typer.Option("INFO")):
    frame=pd.read_parquet(samples) if samples.suffix==".parquet" else pd.read_csv(samples);write_html({"样本预览":frame.head(100)},samples.parent/"report.html");console.print(samples.parent/"report.html")
@backtest_app.command("run")
def backtest_run(start:str=typer.Option(...),end:str=typer.Option(...),config:Path=typer.Option(Path("configs/backtest.yaml")),log_level:str=typer.Option("INFO")):
    start_date=date.fromisoformat(start);end_date=date.fromisoformat(end);cfg,p=context(config);root=create_run(cfg.project.output_dir,"backtest",cfg.model_dump(mode="json"),[start,end]);trades,metrics=run_backtest(p,cfg,start_date,end_date);trades.to_csv(root/"trades.csv",index=False);(root/"metrics.json").write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding="utf-8");summary={k:v for k,v in metrics.items() if k!="height_layers"};layers=pd.DataFrame(metrics["height_layers"]);layers.to_csv(root/"height_layers.csv",index=False);write_html({"交易":trades,"总体指标":pd.DataFrame([summary]),"按连板高度分层":layers},root/"report.html","量化反包回测报告");console.print_json(data=metrics);console.print(root)
@backtest_app.command("report")
def backtest_report(run_dir:Path=typer.Option(...),config:Path=typer.Option(Path("configs/backtest.yaml")),log_level:str=typer.Option("INFO")):
    trades=pd.read_csv(run_dir/"trades.csv");metrics=json.loads((run_dir/"metrics.json").read_text());write_html({"交易":trades,"指标":pd.DataFrame([metrics])},run_dir/"report.html","量化反包回测报告")
@scan_app.command("run")
def scan_run(date_:str=typer.Option(...,"--date"),config:Path=typer.Option(Path("configs/default.yaml")),log_level:str=typer.Option("INFO")):
    signal_date=date.fromisoformat(date_);cfg,p=context(config);root=create_run(cfg.project.output_dir,"scan",cfg.model_dump(mode="json"),[date_,date_]);cs=candidates_for_date(p,signal_date,cfg);frame=pd.DataFrame([c.model_dump() for c in cs]);paths=write_scan(frame,root);console.print(frame[[x for x in ["grade","total_score","symbol","reasons"] if x in frame]] if len(frame) else "无候选");console.print(paths)
if __name__=="__main__":app()
