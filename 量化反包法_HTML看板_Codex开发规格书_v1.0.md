# 量化反包法 HTML 看板开发规格书 v1.0

**用途：直接交给 Codex 开发**  
**项目定位：量化反包法的全链路、可解释、可审计策略驾驶舱**  
**视觉方向：深色 / 黑科技 / 技术风 / 数据终端风**  
**推荐技术栈：React + TypeScript + Vite + Tailwind CSS + ECharts + TanStack Table + FastAPI**

---

## 0. Codex 执行总指令

请严格按照本文档开发，不要自行简化“可解释性”和“决策审计”功能。

本项目不是普通股票列表页，也不是只展示最终买入信号的 Dashboard。核心要求是：

> 任意日期、任意股票，都必须能够完整还原程序当时使用了什么数据、执行了哪些规则、每个指标是多少、阈值是多少、每一步 PASS / FAIL / NOT_RUN / NO_DATA / ERROR 的结果、为什么进入候选池、为什么被淘汰、为什么可以买入、为什么没有买、为什么卖出。

前端不得自行推断策略结论。所有策略判断、评分、原因、阈值、公式结果必须由后端策略引擎返回，前端只负责展示。

开发优先级：
1. 决策链完整；
2. 数据字段完整；
3. 页面可追溯；
4. 任何分数都能拆解；
5. 任何淘汰都能解释；
6. 任何买卖都能还原；
7. 视觉保持深色、克制、专业的技术终端风格。

---

## 1. 项目目标

系统同时服务三类视角。

### 1.1 管理视角
关注：今天筛了多少股票、候选多少、买入多少、持仓多少、今日盈亏、哪个环节淘汰最多、策略是否正常运行。

### 1.2 交易员视角
关注：哪些股票当前可买、为什么可买、触发了哪些条件、还有哪些条件没确认、当前状态走到哪一步、买入和退出原因是什么。

### 1.3 研究员视角
关注：每个因子实际值、阈值、公式、历史基线、分数贡献、被淘汰股票后续表现、某条规则是否过滤过严、不同策略版本表现差异。

---

## 2. 核心设计原则

### 2.1 全链路可审计

标准链路：

```text
Universe
↓
TradableFilter
↓
BoardPattern
↓
FirstBreak
↓
SectorFilter
↓
MA5Filter
↓
AuctionFilter
↓
IntradayConfirmation
↓
BuySignal
↓
Order
↓
Position
↓
ExitSignal
↓
Closed
```

任意股票在任意阶段停止，都必须显示：停在哪一步、为什么、哪条规则失败、实际值、阈值、后续阶段为什么没执行。

### 2.2 统一五态

所有规则统一：

```text
PASS
FAIL
NOT_RUN
NO_DATA
ERROR
```

- PASS：执行并通过
- FAIL：执行但不满足
- NOT_RUN：前置阶段失败，因此未执行
- NO_DATA：缺少必要数据
- ERROR：规则计算异常

禁止用 null 同时表示多个状态。

### 2.3 前端不做策略判断

错误：

```ts
if (auctionVolumeRatio >= 2.5) showPass()
```

正确：后端直接返回判断结果。

```json
{
  "rule_id": "auction_volume_ratio",
  "actual_value": 4.31,
  "operator": ">=",
  "threshold": 2.5,
  "status": "PASS",
  "score": 8,
  "max_score": 8,
  "reason": "竞价成交量显著高于20日历史中位数"
}
```

---

## 3. 视觉设计规范

### 3.1 风格关键词

深色、黑科技、技术终端、量化研究室、机构交易工作站、专业、克制、高信息密度。

目标感受：

```text
Bloomberg Terminal
+ Quant Research Dashboard
+ Dark DevOps Console
+ Institutional Trading Workstation
```

不要做成游戏 UI、霓虹赛博朋克、紫色渐变 SaaS、大圆角卡片。

### 3.2 Design Tokens

```css
--bg-root: #05070A;
--bg-sidebar: #080B10;
--bg-panel: #0B0F15;
--bg-panel-hover: #10161F;
--bg-elevated: #111821;
--bg-input: #090D13;

--border-primary: #1B2633;
--border-secondary: #121B25;
--border-focus: #2C6E9F;

--text-primary: #E6EDF3;
--text-secondary: #93A4B5;
--text-muted: #5D6B7A;
--text-disabled: #3B4652;

--status-pass: #35D07F;
--status-fail: #FF5D5D;
--status-warning: #F2B84B;
--status-info: #49A8FF;
--status-not-run: #64748B;
--status-no-data: #B07CFF;
--status-error: #FF3B8D;

--signal-watch: #F2B84B;
--signal-buy: #35D07F;
--signal-hold: #49A8FF;
--signal-sell: #FF7A45;
--signal-closed: #64748B;
```

颜色只用于状态和重点，不用于大面积装饰。

### 3.3 字体

中文 UI：
Inter / PingFang SC / Microsoft YaHei

关键数字：
JetBrains Mono / IBM Plex Mono / SFMono-Regular

例如：

```text
86 / 100
4.31x
-2.14%
09:41:03
```

### 3.4 密度

```text
Table row height: 36~40px
Panel padding: 16px
Section gap: 12~16px
Border radius: 4~8px
```

---

## 4. 全局页面框架

桌面优先，最小 1280px。

```text
┌─────────────────────────────────────────────────────┐
│ Top Bar                                             │
├────────────┬────────────────────────────────────────┤
│ Sidebar    │ Main Content                           │
│            │                                        │
└────────────┴────────────────────────────────────────┘
```

Sidebar 菜单：

```text
Dashboard
Pipeline
Candidates
Decision Audit
Trades
Sectors
Research
Backtest
Runs
Config
```

底部显示：

```text
Strategy v0.3.4
Config 2026-08-17-A
API Connected
```

Top Bar：

- 当前交易日
- 数据更新时间
- Strategy Version
- Config Version
- Data Source 状态
- API 状态
- 全局股票搜索

任意股票都可搜索，即使它未进入候选池。

---

## 5. Dashboard 今日总览

路由：

```text
/dashboard
```

### 5.1 KPI

```text
全市场股票
可交易股票
基础候选
竞价候选
盘中触发
实际买入
持仓
今日策略收益
```

### 5.2 策略漏斗

```text
全市场             5342
  ↓
可交易             4817
  ↓
2~3板               63
  ↓
首次断板             21
  ↓
MA5合格              14
  ↓
板块合格              9
  ↓
竞价合格              5
  ↓
盘中触发              2
  ↓
成交                  2
```

点击任意一级跳转 Pipeline 并自动带筛选条件。

### 5.3 今日候选

列：

```text
股票
当前状态
总分
连板
首次断板
SectorScore
MA5Distance
AuctionScore
Intraday
最终结论
```

### 5.4 淘汰原因分布

横向 Bar Chart，例如：

```text
非2~3板          4754
非首次断板         42
MA5不合格           7
板块弱              5
竞价量比不足         3
开盘未转强           2
```

点击原因跳转对应股票列表。

### 5.5 板块强度

列：

```text
板块
SectorScore
涨停家数
上涨比例
梯队
候选股票数
```

### 5.6 策略运行时间线

```text
09:20:01 Universe loaded                5342
09:20:04 Tradable filter completed      4817
09:20:09 Board pattern completed          63
09:20:13 First break completed            21
09:25:03 Auction data updated            4817
09:25:05 Auction filter completed           5
09:41:02 002XXX intraday trigger
09:42:00 BUY SIGNAL generated
09:43:00 Order filled @ 18.63
```

---

## 6. Pipeline 全市场筛选流水

路由：

```text
/pipeline
```

必须能显示所有股票。

主表列：

```text
股票代码
股票名称
最终状态
当前阶段
BoardPattern
FirstBreak
Sector
MA5
Auction
Intraday
Score
淘汰原因
最后更新时间
```

功能：

- server-side pagination
- virtualization
- 排序
- 列筛选
- 按阶段过滤
- 按状态过滤
- 按淘汰原因过滤
- 日期查询
- CSV 导出

点击股票先打开右侧 Drawer：

```text
Universe             PASS
Tradable             PASS
BoardPattern         PASS
FirstBreak           PASS
Sector               PASS
MA5                  PASS
Auction              FAIL
Intraday             NOT_RUN
BuySignal            NOT_RUN
```

Drawer 底部按钮：

```text
打开完整决策审计
```

---

## 7. Candidates 候选股票池

路由：

```text
/candidates
```

Tabs：

```text
全部
A级
B级
观察
BUY SIGNAL
已买入
已淘汰
```

列：

```text
股票
状态
总分
等级
连板
断板
板块
MA5
竞价
开盘确认
触发时间
结论
```

等级阈值必须来自后端 Config，不得前端硬编码。

---

## 8. Decision Audit 个股决策审计

路由：

```text
/stock/:symbol?date=2026-08-17
```

这是整个系统的核心页面。

Header 示例：

```text
机器人股份
002XXX

BUY SIGNAL
86 / 100

Strategy v0.3.4
Config 2026-08-17-A
```

主要理由：

```text
✓ 3连板后首次断板
✓ 板块强度 18/20
✓ MA5距离 +0.63%
✓ 竞价量比 4.31x
✓ 竞价低开 -2.14%
✓ 8分钟翻红
✓ Open5mVolumeRatio 3.7x
```

失败股票：

```text
REJECT

主要原因：
竞价量比不足

淘汰阶段：
AuctionFilter
```

Tabs：

```text
Overview
Decision Trace
Metrics
Chart
Raw Data
```

---

## 9. Overview

显示：

```text
系统结论
BUY

等级
A

总分
86 / 100

当前阶段
BuySignal

信号时间
09:42:00
```

Score Breakdown：

```text
StockStrength      19 / 20
Sector             18 / 20
FirstBreak         15 / 15
MA5                14 / 15
Auction            18 / 20
Market              2 / 10

TOTAL              86 / 100
```

每项支持继续展开。

---

## 10. Decision Trace

纵向时间线：

```text
01 Universe
PASS

02 TradableFilter
PASS

03 BoardPattern
PASS
3连板

04 FirstBreak
PASS
本轮上涨首次断板

05 Sector
PASS
18 / 20

06 MA5
PASS
Distance +0.63%

07 Auction
PASS
18 / 20

08 Intraday
PASS
8分钟翻红

09 BuySignal
TRIGGERED
09:42:00

10 Order
FILLED
09:43:00 @ 18.63

11 Position
OPEN
```

点击任意节点展开全部 Rule Evaluation。

---

## 11. Rule Evaluation Card

开发通用组件：

```tsx
<RuleEvaluationCard />
```

示例：

```text
竞价量比

4.31x

条件
>= 2.50x

PASS

Score
8 / 8
```

展开：

```text
说明
今日竞价成交量显著高于过去20日竞价成交量中位数

公式
AuctionVolume / Median(AuctionVolume[-20:])

Inputs
todayAuctionVolume = 1,320,000
historyMedian = 306,270

计算
1320000 / 306270 = 4.31
```

---

## 12. Metrics

按分组：

```text
Price
Board Pattern
Sector
MA
Auction
Intraday
Market
Liquidity
Risk
```

表格列：

```text
指标
实际值
历史值
阈值
状态
评分
更新时间
```

允许按指标名搜索。

---

## 13. Chart

使用 ECharts 或 TradingView Lightweight Charts。

支持：

```text
Daily
1m
5m
```

日 K 标记：

- MA5
- 涨停
- 2板
- 3板
- 首次断板
- 候选日
- 买入
- 卖出

分钟图标记：

```text
09:25 Auction
09:30 Open
09:36 Touch MA5
09:38 Recover MA5
09:41 Turn Red
09:42 BUY SIGNAL
09:43 FILLED
```

所有事件必须来自后端 Event API。

---

## 14. Raw Data

必须存在。

Tabs：

```text
Daily Bars
Minute Bars
Auction
Sector Snapshot
Market Snapshot
Factor Inputs
```

用于验证程序真实使用的数据。

例如用户看到：

```text
AuctionVolumeRatio = 4.31
```

必须能继续看到：

```text
today auction volume
past 20-day auction volumes
median
```

---

## 15. Rejections 淘汰股票

路由：

```text
/rejections
```

列：

```text
股票
淘汰阶段
首要失败规则
实际值
阈值
总分
后续最高涨幅
次日最高涨幅
后续收盘收益
```

即使被淘汰，也要继续记录后续表现。

### Rejected Outcome

至少保存：

```text
D0 close return
D0 max return
D1 open return
D1 max return
D1 close return
D2 max return
```

用于研究某个过滤条件是否过严。

---

## 16. Sectors 板块页

路由：

```text
/sectors
```

主表：

```text
板块
SectorScore
涨停数
上涨比例
Top5Return
LadderScore
SectorAge
候选数
买入数
```

板块详情：

```text
机器人
SectorScore 18 / 20
```

评分拆解：

```text
涨停家数        5 / 5
上涨比例        5 / 5
前排强度        4 / 4
梯队完整        3 / 3
持续性          1 / 3
```

显示板块涨停梯队和板块内候选。

---

## 17. Trades 交易记录

路由：

```text
/trades
```

列：

```text
Trade ID
股票
买入日期
买入价
买入原因
卖出日期
卖出价
卖出原因
收益率
MFE
MAE
持仓时间
策略版本
```

交易详情 Timeline：

```text
09:25 Auction PASS
09:38 MA5 recovered
09:41 Turned red
09:42 BUY SIGNAL
09:43 FILLED 18.63

D+1
10:03 EXIT SIGNAL
10:04 SOLD 20.15
```

---

## 18. Runs 程序运行日志

路由：

```text
/runs
```

每次运行保存：

```text
run_id
trade_date
strategy_version
config_version
start_at
finish_at
duration
status
data_source
records
errors
```

不要要求用户阅读服务器日志。

---

## 19. Config 参数中心

路由：

```text
/config
```

V1.0 只读。

示例：

```yaml
board_pattern:
  min_boards: 2
  max_boards: 3

ma5:
  min_distance: -0.02
  max_distance: 0.03

auction:
  min_volume_ratio: 2.5
  min_return: -0.05
  max_return: 0.03

intraday:
  confirm_window_minutes: 30
  max_minutes_to_red: 15
  min_open_5m_volume_ratio: 2.0
```

显示：

```text
Strategy Version
Config Version
Effective Date
Created At
Git Commit SHA
```

---

## 20. Research / Backtest

V0.2 开发。

Research：

- 因子分桶
- 胜率
- 盈亏比
- 阈值敏感性
- Rejected Outcome
- 因子相关性

Backtest：

- 回测区间
- 策略版本
- 配置版本
- 总交易数
- 胜率
- 平均收益
- 盈亏比
- Profit Factor
- 最大回撤
- 最大连续亏损
- 权益曲线
- 月度收益
- 分年度收益

---

## 21. 后端核心 DTO

### RuleEvaluation

```python
class RuleEvaluation(BaseModel):
    rule_id: str
    rule_name: str
    stage: str
    actual_value: Any | None
    operator: str | None
    threshold: Any | None
    status: Literal["PASS", "FAIL", "NOT_RUN", "NO_DATA", "ERROR"]
    score: float | None
    max_score: float | None
    reason: str | None
    formula: str | None
    inputs: dict[str, Any] | None
    evaluated_at: datetime | None
```

### StageEvaluation

```python
class StageEvaluation(BaseModel):
    stage_id: str
    stage_name: str
    status: str
    score: float | None
    max_score: float | None
    rules: list[RuleEvaluation]
    primary_reason: str | None
    started_at: datetime | None
    completed_at: datetime | None
```

### DecisionTrace

```python
class DecisionTrace(BaseModel):
    trade_date: date
    symbol: str
    name: str
    strategy_version: str
    config_version: str
    final_status: str
    current_stage: str
    total_score: float | None
    max_score: float | None
    primary_reason: str | None
    stages: list[StageEvaluation]
    signal: dict | None
    order: dict | None
    position: dict | None
```

### Candidate

```python
class Candidate(BaseModel):
    trade_date: date
    symbol: str
    name: str
    status: str
    score: float
    grade: str
    board_count: int | None
    is_first_break: bool | None
    sector_id: str | None
    sector_name: str | None
    sector_score: float | None
    ma5_distance: float | None
    auction_score: float | None
    auction_return: float | None
    auction_volume_ratio: float | None
    intraday_status: str | None
    signal_time: datetime | None
    primary_reason: str | None
```

### PipelineRecord

```python
class PipelineRecord(BaseModel):
    trade_date: date
    symbol: str
    name: str
    final_status: str
    current_stage: str
    stage_statuses: dict[str, str]
    total_score: float | None
    rejection_stage: str | None
    rejection_rule: str | None
    rejection_reason: str | None
    updated_at: datetime
```

---

## 22. API 规范

统一前缀：

```text
/api/v1/
```

Dashboard：

```text
GET /api/v1/dashboard/summary?date=...
GET /api/v1/dashboard/funnel?date=...
GET /api/v1/dashboard/rejection-stats?date=...
```

Pipeline：

```text
GET /api/v1/pipeline?date=...
```

支持 query：

```text
stage
status
rejection_reason
page
page_size
sort
```

Candidates：

```text
GET /api/v1/candidates?date=...
```

Stock Audit：

```text
GET /api/v1/stocks/{symbol}/decision?date=...
GET /api/v1/stocks/{symbol}/metrics?date=...
GET /api/v1/stocks/{symbol}/events?date=...
GET /api/v1/stocks/{symbol}/bars/daily
GET /api/v1/stocks/{symbol}/bars/minute
GET /api/v1/stocks/{symbol}/raw?date=...
```

Sectors：

```text
GET /api/v1/sectors?date=...
GET /api/v1/sectors/{sector_id}?date=...
```

Trades：

```text
GET /api/v1/trades
GET /api/v1/trades/{trade_id}
```

Runs：

```text
GET /api/v1/runs
GET /api/v1/runs/{run_id}
```

Config：

```text
GET /api/v1/config/current
GET /api/v1/config/versions
GET /api/v1/config/{version}
```

---

## 23. 前端目录

```text
frontend/
├─ src/
│  ├─ app/
│  │  ├─ App.tsx
│  │  ├─ router.tsx
│  │  └─ providers.tsx
│  ├─ pages/
│  │  ├─ Dashboard/
│  │  ├─ Pipeline/
│  │  ├─ Candidates/
│  │  ├─ StockAudit/
│  │  ├─ Rejections/
│  │  ├─ Sectors/
│  │  ├─ Trades/
│  │  ├─ Research/
│  │  ├─ Backtest/
│  │  ├─ Runs/
│  │  └─ Config/
│  ├─ components/
│  │  ├─ layout/
│  │  ├─ status/
│  │  ├─ rules/
│  │  ├─ charts/
│  │  ├─ tables/
│  │  ├─ stock/
│  │  └─ common/
│  ├─ api/
│  ├─ types/
│  ├─ hooks/
│  ├─ utils/
│  ├─ styles/
│  ├─ mocks/
│  └─ constants/
├─ public/
├─ package.json
└─ vite.config.ts
```

---

## 24. 核心组件

```text
AppShell
Sidebar
TopBar
StatusBadge
StageStatusBadge
MetricCard
KpiCard
RuleEvaluationCard
RuleEvaluationTable
DecisionTraceTimeline
ScoreBreakdown
StrategyFunnel
CandidateTable
PipelineTable
RejectionTable
StockHeader
StockReasonList
DailyKChart
MinuteKChart
AuctionPanel
RunTimeline
ConfigViewer
```

---

## 25. 数据持久化建议

MVP：

```text
Parquet + DuckDB
```

建议表：

```text
pipeline_records
decision_traces
rule_evaluations
candidates
stock_metrics
stock_events
sector_snapshots
strategy_runs
trades
rejected_outcomes
configs
```

`rule_evaluations` 至少：

```text
trade_date
symbol
decision_id
stage
rule_id
rule_name
actual_value_json
operator
threshold_json
status
score
max_score
reason
formula
inputs_json
strategy_version
config_version
evaluated_at
```

`stock_events`：

```text
trade_date
symbol
timestamp
event_type
event_name
value
metadata_json
```

事件：

```text
AUCTION
OPEN
TOUCH_MA5
RECOVER_MA5
TURN_RED
BUY_SIGNAL
ORDER_FILLED
EXIT_SIGNAL
ORDER_CLOSED
```

---

## 26. Mock 模式

后端未完成前必须支持：

```env
VITE_USE_MOCK=true
```

Mock 至少覆盖：

1. 完整通过并 BUY；
2. Auction FAIL；
3. Sector FAIL；
4. NO_DATA；
5. ERROR；
6. 已卖出交易。

Mock DTO 必须和正式 API 完全一致。

---

## 27. 性能与 URL

Pipeline 支持至少 6000 股票，使用：

- server-side pagination
- virtualization
- TanStack Query cache
- memoization

URL 必须可复现筛选状态：

```text
/pipeline?date=2026-08-17&stage=Auction&status=FAIL
```

日期默认使用 `latest available trading day`，不是简单取系统日期。

---

## 28. Loading / Error / Empty / Stale

页面必须区分：

```text
Loading
Empty
Error
Partial Data
Stale Data
```

数据过期时显示：

```text
STALE DATA
Last Update 09:21:03
```

API 错误：

```text
DATA REQUEST FAILED
Endpoint /api/v1/candidates
Request ID REQ-xxx
Retry
```

---

## 29. 版本与审计 ID

任何决策绑定：

```text
strategy_version
config_version
code_commit
run_id
decision_id
```

例如：

```text
Decision ID
DEC-20260817-002XXX-000042

Run ID
RUN-20260817-092500
```

---

## 30. 前端测试

推荐：

```text
Vitest
React Testing Library
Playwright
```

核心单测：

1. PASS / FAIL / NOT_RUN 正确显示；
2. RuleEvaluationCard 显示实际值和阈值；
3. ScoreBreakdown 正确；
4. Pipeline 筛选；
5. URL query 状态恢复；
6. DecisionTrace 顺序；
7. NO_DATA / ERROR 不被当成 FAIL；
8. Mock API 正常。

核心 E2E：

### Test 1
Dashboard → 点击候选 → 打开个股审计。

### Test 2
Pipeline → Auction FAIL → 打开股票。

### Test 3
被 Auction 淘汰的股票必须显示：

```text
Intraday = NOT_RUN
```

### Test 4
BUY 股票完整显示：

```text
Auction PASS
Intraday PASS
BuySignal TRIGGERED
Order FILLED
```

---

## 31. V0.1 强制范围

必须交付：

```text
Dashboard
Pipeline
Candidates
Stock Decision Audit
Rejections
Trades
Runs
Config
Daily/Minute Chart
Rule Evaluation
Decision Trace
Score Breakdown
```

暂不优先：

- 用户系统
- 权限
- 云部署
- 实盘交易
- WebSocket
- 手机端
- 新闻 NLP
- AI 自动解释
- 网页修改策略参数
- PostgreSQL

---

## 32. 开发阶段

### Phase UI-1
初始化 Vite/React/TS/Tailwind/Router，完成 AppShell、Sidebar、TopBar、Design Tokens。

### Phase UI-2
Dashboard：KPI、Funnel、候选、淘汰原因、Run Timeline。

### Phase UI-3
Pipeline：全市场表、筛选、Drawer、RuleEvaluationCard。

### Phase UI-4
Decision Audit：Overview、Decision Trace、Metrics、Score Breakdown。

### Phase UI-5
Daily/Minute K、Events、Auction Panel、Raw Data。

### Phase UI-6
Trades、Sectors、Runs、Config。

### Phase UI-7
Rejected Outcome、Research、Backtest。

---

## 33. 验收标准

### 33.1 为什么选它

给定 date + symbol，最多两次点击内必须看到：

- 所有关键指标；
- 评分；
- 选择原因。

### 33.2 为什么淘汰

必须显示：

```text
淘汰阶段
失败规则
实际值
阈值
失败原因
```

### 33.3 NOT_RUN 正确

前置 FAIL 后，后续不得显示为 FAIL。

必须：

```text
NOT_RUN
由于 AuctionFilter 已失败，IntradayConfirmation 未执行。
```

### 33.4 评分透明

86 分必须能拆：

```text
19 + 18 + 15 + 14 + 18 + 2 = 86
```

并继续拆到每条 Rule。

### 33.5 数据可追踪

任意指标至少能查看：

```text
value
threshold
status
formula
inputs
```

### 33.6 原始数据可验证

AuctionVolumeRatio=4.31 必须能查到今日竞价量、20日历史值和中位数。

### 33.7 图表事件

买入股票分钟图至少标：

```text
Auction
Open
Recover MA5
Turn Red
Buy Signal
Fill
```

### 33.8 无隐藏因子

凡是代码中对最终选择有影响的指标、条件、评分、状态、信号，都必须在 UI 中能找到。

---

## 34. Dashboard Wireframe

```text
┌────────────────────────────────────────────────────────────────────┐
│ QUANT REVERSAL                        2026-08-17   DATA ● LIVE     │
│ Strategy v0.3.4  Config 2026-08-17-A              09:41:12        │
├──────────────┬─────────────────────────────────────────────────────┤
│ Dashboard    │  MARKET  TRADABLE  CANDIDATE  SIGNAL  POSITION     │
│ Pipeline     │   5342      4817       21        2        2         │
│ Candidates   │                                                     │
│ Decision     │  ┌──────────── Strategy Funnel ────────────────┐   │
│ Trades       │  │ 5342 → 4817 → 63 → 21 → 14 → 9 → 5 → 2    │   │
│ Sectors      │  └─────────────────────────────────────────────┘   │
│ Research     │                                                     │
│ Backtest     │  CANDIDATES                 REJECTION REASONS       │
│ Runs         │  ┌─────────────────────┐    ┌───────────────────┐   │
│ Config       │  │002XXX  BUY  86      │    │Not Board  4754   │   │
│              │  │600XXX WATCH 78      │    │Auction      3     │   │
│              │  │300XXX FAIL  64      │    │Sector       5     │   │
│              │  └─────────────────────┘    └───────────────────┘   │
│              │                                                     │
│              │  STRATEGY RUN TIMELINE                              │
│              │  09:25 Auction filter complete                      │
│              │  09:41 002XXX intraday trigger                      │
└──────────────┴─────────────────────────────────────────────────────┘
```

---

## 35. Decision Audit Wireframe

```text
┌────────────────────────────────────────────────────────────────────┐
│ 002XXX 机器人股份                     BUY SIGNAL       86 / 100   │
│ 2026-08-17  Strategy v0.3.4  Config A                              │
├────────────────────────────────────────────────────────────────────┤
│ WHY SELECTED                                                       │
│ ✓ 3板首次断板  ✓ Sector 18/20  ✓ MA5 +0.63%                       │
│ ✓ Auction 4.31x ✓ 8min Turn Red ✓ Open5m 3.7x                    │
├───────────────────────────────┬────────────────────────────────────┤
│ DECISION TRACE                │ SCORE BREAKDOWN                    │
│ Universe        PASS          │ Stock        19 / 20               │
│ Tradable        PASS          │ Sector       18 / 20               │
│ BoardPattern    PASS          │ FirstBreak   15 / 15               │
│ FirstBreak      PASS          │ MA5          14 / 15               │
│ Sector          PASS          │ Auction      18 / 20               │
│ MA5             PASS          │ Market        2 / 10               │
│ Auction         PASS          │ TOTAL        86 / 100              │
│ Intraday        PASS          │                                    │
│ BuySignal       TRIGGERED     │                                    │
│ Order           FILLED        │                                    │
├───────────────────────────────┴────────────────────────────────────┤
│ DAILY / 1M CHART                                                   │
├────────────────────────────────────────────────────────────────────┤
│ RULE EVALUATIONS                                                   │
│ AuctionVolumeRatio   4.31x   >=2.50   PASS   +8/8                 │
│ AuctionReturn       -2.14%   [-5,+3]  PASS   +4/5                 │
│ MA5Distance         +0.63%   [-2,+3]  PASS  +14/15                │
└────────────────────────────────────────────────────────────────────┘
```

---

## 36. Codex 第一批任务

请先完成以下范围，不要同时开太多模块：

### Task A
初始化 `frontend/`：

```text
React
TypeScript
Vite
Tailwind CSS
React Router
TanStack Query
TanStack Table
ECharts
```

### Task B
建立深色 Design Tokens，并实现：

```text
AppShell
Sidebar
TopBar
StatusBadge
MetricCard
RuleEvaluationCard
```

### Task C
创建 Mock API：

```text
dashboard
pipeline
candidates
stock decision
stock metrics
stock events
trades
runs
config
```

### Task D
完成 Dashboard。

### Task E
完成 Pipeline。

### Task F
完成 Stock Decision Audit。

这三个核心页面验收后，再开发其他模块。

---

## 37. Codex 每个阶段完成时必须输出

```text
1. 完成了什么
2. 创建/修改了哪些文件
3. 如何运行
4. 如何测试
5. 页面截图或预览结果
6. 未完成事项
7. 已知问题
```

不要只回复 `done`。

---

## 38. 最终成功标准

当用户问：

> 为什么今天没选 002XXX？

系统能显示：

```text
002XXX

BoardPattern       PASS
FirstBreak         PASS
MA5                PASS
Sector             PASS
Auction            FAIL

失败规则：
AuctionVolumeRatio

实际值：
1.42x

要求：
>= 2.50x

因此：
未进入 IntradayConfirmation

Intraday:
NOT_RUN
```

当用户问：

> 为什么买了 600XXX？

系统能显示：

```text
3连板首次断板
+
SectorScore 18
+
MA5Distance +0.63%
+
AuctionVolumeRatio 4.31
+
竞价低开 -2.14%
+
8分钟翻红
+
Open5mVolumeRatio 3.7
=
BUY SIGNAL
```

并且每个数字可以继续向下追到公式和原始数据。

---

## 39. 不可删减的核心资产

任何重构中都不得删除：

1. DecisionTrace
2. RuleEvaluation
3. PASS / FAIL / NOT_RUN / NO_DATA / ERROR
4. Strategy Version
5. Config Version
6. 淘汰原因
7. 原始值
8. 阈值
9. 公式
10. Inputs
11. Rejected Outcome
12. Raw Data
13. Run Log
14. 图表事件
15. 任意股票可查询

这些是本项目区别于普通量化 Dashboard 的核心。
