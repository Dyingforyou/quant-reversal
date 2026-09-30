import {useQuery} from '@tanstack/react-query';
import {Download,Filter,PanelRightClose,Search,X} from 'lucide-react';
import {useMemo,useState} from 'react';
import {Link,useSearchParams} from 'react-router-dom';
import {api} from '../api/client';
import {StageDot,StatusBadge,statusLabel} from '../components/StatusBadge';
import type {PipelineRecord} from '../types';

const stages=['BoardHeightDetection','StrategyRouter','HeightModel','FirstBreak','Auction','Intraday'];
const stageLabel:Record<string,string>={Universe:'股票池',Tradable:'可交易',BoardHeightDetection:'高度识别',StrategyRouter:'模型路由',HeightModel:'高度模型',FirstBreak:'首次断板',Auction:'竞价',Intraday:'盘中确认',BuySignal:'买入信号'};

export default function Pipeline(){
 const {data=[]}=useQuery({queryKey:['pipeline'],queryFn:api.pipeline});
 const [params,setParams]=useSearchParams();const [query,setQuery]=useState('');const [selected,setSelected]=useState<PipelineRecord|null>(null);
 const status=params.get('status')??'ALL';
 const rows=useMemo(()=>data.filter(x=>(status==='ALL'||x.final_status===status)&&(x.symbol.includes(query)||x.name.includes(query))),[data,status,query]);
 return <div className="page">
  <div className="page-title"><div><span className="eyebrow">全市场决策追踪</span><h1>全市场筛选流水</h1><p>高度识别 → 模型路由 → 低位/中位/高标模型 → 后续评分</p></div><button className="button"><Download size={14}/> 导出表格</button></div>
  <div className="toolbar"><div className="searchbox"><Search size={14}/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="代码 / 名称"/></div><div className="filter-label"><Filter size={13}/> 最终状态</div>{['ALL','BUY SIGNAL','WATCH','REJECT','NO_DATA'].map(s=><button className={status===s?'active':''} onClick={()=>{params.set('status',s);setParams(params)}} key={s}>{s==='ALL'?'全部':statusLabel(s)}</button>)}<span className="toolbar-count">共 {rows.length} 条记录</span></div>
  <section className="panel pipeline-table"><div className="data-table"><table><thead><tr><th>股票代码 / 名称</th><th>高度模型</th><th>高度排名</th><th>最高板</th><th>最终状态</th>{stages.map(s=><th key={s}>{stageLabel[s]}</th>)}<th>评分</th><th>结论</th></tr></thead><tbody>{rows.map(row=><tr key={row.symbol} onClick={()=>setSelected(row)}><td><div className="stock"><b>{row.symbol}</b><span>{row.name}</span></div></td><td>{row.board_height}板<small>{row.sub_strategy}</small></td><td>第{row.height_rank}档</td><td>{row.market_highest?'是':'否'}</td><td><StatusBadge status={row.final_status}/></td>{stages.map(s=><td className="stage-cell" key={s}><StageDot status={row.stage_statuses[s]}/><small>{statusLabel(row.stage_statuses[s])}</small></td>)}<td><strong>{row.total_score??'—'}</strong><small>{row.grade==='—'?'—':`${row.grade}级`}</small></td><td className="reason">{row.model_route_reason}<br/>{row.rejection_reason??'—'}</td></tr>)}</tbody></table></div><div className="pagination"><span>显示第 1–{rows.length} 条</span></div></section>
  {selected&&<div className="drawer-backdrop" onClick={()=>setSelected(null)}><aside className="drawer" onClick={e=>e.stopPropagation()}><div className="drawer-head"><div><span className="eyebrow">模型路由追踪</span><h2>{selected.symbol} <small>{selected.name}</small></h2></div><button onClick={()=>setSelected(null)}><X/></button></div><div className="drawer-result"><StatusBadge status={selected.final_status}/><b>{selected.board_height}板<small>{selected.sub_strategy}</small></b></div><div className="rejection-box"><span>模型路由原因</span><b>{selected.model_route_reason}</b><small>高度排名第{selected.height_rank}档 · {selected.market_highest?'全市场最高板':'非最高板'}</small></div><div className="quick-trace">{['Universe','Tradable',...stages,'BuySignal'].map((s,i)=>{const value=i<2?'PASS':selected.stage_statuses[s]??(selected.final_status==='BUY SIGNAL'?'PASS':'NOT_RUN');return <div key={s}><span>{String(i+1).padStart(2,'0')}</span><b>{stageLabel[s]}</b><StatusBadge status={value}/></div>})}</div><Link className="drawer-link" to={`/stock/${selected.symbol}`}>打开完整决策审计 <PanelRightClose size={15}/></Link></aside></div>}
 </div>;
}
