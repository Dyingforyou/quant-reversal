# quant-reversal

A股“2板以上首次断板 → 高度模型路由 → 竞价承接 → 盘中确认 → T+1退出”的可解释研究、回测与扫描工具。2～3板、4～5板、6板以上分别进入低位、中位和高标子模型；所有分层阈值和权重均为待历史样本验证的假设。

## 安装与最短运行路径

```bash
python3 -m venv .venv
source .venv/bin/activate                 # PowerShell: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"

quant-reversal data validate --config configs/default.yaml
quant-reversal research build-samples --start 2024-01-01 --end 2024-12-31 --config configs/research.yaml
quant-reversal backtest run --start 2024-01-01 --end 2024-12-31 --config configs/backtest.yaml
quant-reversal scan run --date 2024-02-09 --config configs/default.yaml
pytest
```

## HTML 策略看板

看板位于 `frontend/`，当前使用与正式 API DTO 完全一致的 Mock 数据，覆盖 Dashboard、Pipeline、Candidates 和个股 Decision Audit。

```bash
cd frontend
npm install
npm run dev       # http://localhost:5173
npm test
npm run build
```

推荐审计示例：

- `/stock/002889`：完整通过并成交；
- `/stock/600118`：Auction FAIL，Intraday 为 NOT_RUN；
- `/stock/300024`：Sector FAIL；
- `/stock/688256`：Auction NO_DATA。

首次执行时会在 `data/fixtures` 创建确定性的 Parquet 合成数据。接入真实数据时按 `docs/data_contract.md` 放置标准化文件；策略层不调用第三方 API。

## 免费数据混合采集

真实数据保存到 `data/normalized`：Tushare 提供日线、交易日历和每日涨跌停价；AKShare 提供近期一分钟线，并且只在返回结果中确实存在 `09:25` 记录时保存竞价快照。程序绝不会用 `09:30` 第一根分钟线冒充集合竞价。

```bash
source .venv/bin/activate
pip install -e ".[data,dev]"

export TUSHARE_TOKEN="你的令牌"
quant-reversal data collect-daily \
  --start 2026-07-01 --end 2026-08-17 \
  --symbols 000001,600519 --output data/normalized

# 建议在交易日 15:30 后执行；免费接口通常只能取得近期分钟数据
quant-reversal data collect-intraday \
  --date 2026-08-17 --symbols 000001,600519 \
  --output data/normalized
```

命令可重复执行，数据按主键覆盖并原子写入。若某股票没有独立的 `09:25` 行，程序不会生成竞价记录，并把缺失项写入 `data/normalized/collection_warnings.jsonl`。积累至少 20 个交易日后，竞价量比基线才具有实际意义。

`configs/real.yaml` 指向真实数据目录。真实目录缺数据时程序会明确报错，不会自动混入合成数据。板块归属目前仍需按 `docs/data_contract.md` 补充 `sector_membership.parquet` 后才能运行完整策略扫描。

全市场自动筛选可使用：

```bash
quant-reversal data collect-market --date 2026-08-18 --lookback-days 45
```

该命令按交易日批量获取全市场日线，使用前一交易日的“2～10板后首次断板”结构生成研究池 `base_pool_YYYYMMDD.csv`，随后按高度路由模型并为研究候选采集分钟及竞价。研究入池不等于买入，不满足后续规则的样本仍会保留。

仅调整研究规则时可执行 `quant-reversal data rebuild-pool --date YYYY-MM-DD --output data/normalized`，直接用本地真实日线幂等重建股票池，无需重复下载行情。回测报告强制生成 `height_layers.csv`，包含2板、3板、4板、5板、6板、7板和8板以上分层指标。

盘中运行拆分为股票池准备、全市场竞价基线、候选竞价和候选分钟线。应在前一交易日收盘后准备股票池，信号日 09:26 先用腾讯免费行情批量保存全市场竞价快照，再用多数据源核验候选股竞价；09:31～10:01 每分钟增量采集候选分钟线，收盘后再补齐归档。全市场快照覆盖率达到 80% 才计入 20 个交易日基线，进度保存在 `market_auction_progress.json` 并显示在看板；同日重跑不会重复计数，全市场采集失败也不会阻断候选股监控。

看板不再回退到前端 Mock。定时归档确认 `data/normalized/daily_bars.parquet` 存在且非空后，才会清理 `data/fixtures`、旧的模拟运行输出和 Mock 源文件；真实数据验证失败时拒绝清理。

长期任务使用 `scripts/live_daily.sh`：每个交易日收盘后执行 `prepare` 为下一交易日建池；下一交易日依次执行 `auction`、`minute` 和 `archive`。`current_pool_date.txt` 用于强制校验股票池日期，禁止误用前一日股票池。

## 免费实时行情链路

项目不依赖券商 QMT。盘中分钟行情按 `新浪（完整 OHLCV）→ 腾讯（分钟价与累计量额）→ 东方财富` 自动降级；集合竞价按 `东方财富盘前分钟 → 腾讯 09:25～09:29 快照` 自动降级。腾讯累计成交量、成交额会转换为每分钟增量，并明确标记 `quality=close_and_delta_volume`，不伪装成完整 OHLC。

每轮采集写入 `realtime_health.json`。任一股票超过三分钟没有更新时状态变为 `stale`，同时追加到 `realtime_alerts.jsonl`；看板显示实际最新分钟时间。

## 时间纪律

候选只读取 Signal Day 09:25 可得的竞价及 T-1 前日线；分钟 bar 触发只能在下一分钟开盘成交；卖出必须晚于买入交易日。详见 `docs/no_lookahead.md`。
