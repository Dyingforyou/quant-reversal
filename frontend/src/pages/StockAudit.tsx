import {useQuery} from '@tanstack/react-query';
import {Copy,Database,Info,Search} from 'lucide-react';
import {useState} from 'react';
import {useParams} from 'react-router-dom';
import {api} from '../api/client';
import {PriceChart} from '../components/Charts';
import {RuleEvaluationCard} from '../components/RuleEvaluationCard';
import {StatusBadge} from '../components/StatusBadge';

const scoreNames:Record<string,string>={BoardHeightDetection:'连板高度识别',StrategyRouter:'模型路由',LowHeightReversal:'低位反包模型',MidHeightReversal:'中位反包模型',HighLeaderReversal:'高标反包模型',FirstBreak:'首次断板',Auction:'竞价强度',IntradayConfirmation:'盘中确认'};
const tabNames:Record<string,string>={Overview:'总览','Decision Trace':'决策链',Metrics:'指标明细',Chart:'行情图表','Raw Data':'原始数据'};

export default function StockAudit(){
 const {symbol='002889'}=useParams();const {data,isLoading}=useQuery({queryKey:['decision',symbol],queryFn:()=>api.decision(symbol)});
 const [tab,setTab]=useState('Overview');const [chart,setChart]=useState('1m');
 if(isLoading||!data)return <div className="loading">正在加载决策审计...</div>;
 const rules=data.stages.flatMap(s=>s.rules);const scores=data.stages.filter(s=>s.score!==null);
 const trace=<div className="decision-trace expanded">{data.stages.map((s,i)=><div key={s.stage_id}><span className="trace-index">{String(i+1).padStart(2,'0')}</span><i/><div><b>{scoreNames[s.stage_name]??s.stage_name}</b><small>{s.primary_reason??'规则已完成评估'}</small></div><StatusBadge status={s.status}/><time>{s.completed_at}</time></div>)}</div>;
 return <div className="page audit">
  <section className="stock-hero"><div><span className="eyebrow">决策审计 · {data.trade_date}</span><h1>{data.symbol} <span>{data.name}</span></h1><div className="audit-ids"><span>{data.board_height}板 · {data.height_group}</span><span>{data.sub_strategy}</span><span>高度排名第{data.height_rank}档</span><span>{data.market_highest?'全市场最高板':'非最高板'}</span></div><div className="audit-ids"><span>策略 {data.strategy_version}</span><span>配置 {data.config_version}</span><span>{data.decision_id}</span><button title="复制审计编号"><Copy size={12}/></button></div></div><div className="hero-status"><StatusBadge status={data.final_status}/><strong>{data.total_score??'—'}<small>/ 100</small></strong><span>{data.current_stage}</span></div></section>
  <section className="reason-strip"><span>模型路由</span><div>{data.model_route_reason}</div></section>
  <section className="reason-strip fail-strip"><span>当前结论</span><div><Info size={13}/>{data.primary_reason}</div><small>研究入池不等于买入，缺失数据不会伪造为通过</small></section>
  <div className="tabs">{Object.keys(tabNames).map(x=><button className={tab===x?'active':''} onClick={()=>setTab(x)} key={x}>{tabNames[x]}</button>)}</div>
  {tab==='Overview'&&<><div className="audit-grid"><section className="panel"><div className="panel-head"><div><span className="eyebrow">执行路径</span><h2>决策链</h2></div><span className="muted">{data.run_id}</span></div>{trace}</section><section className="panel"><div className="panel-head"><div><span className="eyebrow">可解释评分</span><h2>评分拆解</h2></div><strong className="total-score">{data.total_score??'—'} / 100</strong></div><div className="score-breakdown">{scores.map(s=><div key={s.stage_id}><span>{scoreNames[s.stage_name]??s.stage_name}</span><div><i style={{width:`${(s.score!/(s.max_score||20))*100}%`}}/></div><b>{s.score}<small> / {s.max_score}</small></b></div>)}</div><div className="audit-callout"><Database size={15}/><div><b>评分由对应高度子模型返回</b><span>前端不计算权重、阈值或总分</span></div></div></section></div><section className="panel rules-panel"><div className="panel-head"><div><span className="eyebrow">规则评估</span><h2>模型路由规则</h2></div><Search size={13}/></div>{rules.map(r=><RuleEvaluationCard rule={r} key={r.rule_id}/>)}</section></>}
  {tab==='Decision Trace'&&<section className="panel">{trace}</section>}
  {tab==='Metrics'&&<section className="panel rules-panel">{rules.map(r=><RuleEvaluationCard rule={r} key={r.rule_id}/>)}</section>}
  {tab==='Chart'&&<section className="panel"><div className="chart-tabs">{[['Daily','日线'],['1m','1分钟'],['5m','5分钟']].map(([key,label])=><button className={chart===key?'active':''} onClick={()=>setChart(key)} key={key}>{label}</button>)}</div><PriceChart minute={chart!=='Daily'}/></section>}
  {tab==='Raw Data'&&<section className="panel raw"><div className="panel-head"><div><span className="eyebrow">因子输入</span><h2>数据状态</h2></div></div><p>封板时间、炸板次数、封单金额等字段在数据源未提供时显示 NO_DATA，不使用推测值。</p></section>}
 </div>;
}
