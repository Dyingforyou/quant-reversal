import {useQuery} from '@tanstack/react-query';
import {ArrowRight,Clock3,ExternalLink} from 'lucide-react';
import {Link} from 'react-router-dom';
import {api} from '../api/client';
import {StatusBadge} from '../components/StatusBadge';

export default function Dashboard(){
 const {data,isLoading}=useQuery({queryKey:['dashboard'],queryFn:api.dashboard,refetchInterval:30000});
 if(isLoading||!data)return <div className="loading">正在加载策略快照...</div>;
 const updated=data.progress.updated_at==='—'?'—':new Date(data.progress.updated_at).toLocaleString('zh-CN',{hour12:false});
 return <div className="page">
  <div className="page-title"><div><span className="eyebrow">策略控制中心</span><h1>今日策略总览</h1><p>仅展示真实采集数据，不使用模拟回退</p></div><div className="live-chip"><i/> 数据采集中</div></div>
  <section className={`execution-progress ${data.progress.status}`}><div className="progress-state"><span>当前阶段</span><b>{data.progress.stage}</b></div><div className="progress-copy"><span>最近完成</span><strong>{data.progress.latest}</strong></div><ArrowRight size={17}/><div className="progress-copy next"><span>下一步</span><strong>{data.progress.next}</strong></div><div className="progress-time"><Clock3 size={12}/>{updated}</div></section>
  <section className="kpi-grid">{data.kpis.map(([name,value,sub],i)=><div className={`kpi ${i===7?'positive':''}`} key={name}><span>{name}</span><b>{value}</b><small>{sub}</small></div>)}</section>
  <section className="panel funnel-panel"><div className="panel-head"><div><span className="eyebrow">筛选转化路径</span><h2>策略筛选漏斗</h2></div><Link to="/pipeline">查看完整流水 <ArrowRight size={14}/></Link></div>{data.funnel.length?<div className="funnel">{data.funnel.map(([name,val],i)=><Link to={`/pipeline?stage=${encodeURIComponent(name)}`} key={name} className="funnel-step"><span>{String(i+1).padStart(2,'0')}</span><b>{val.toLocaleString()}</b><small>{name}</small>{i<data.funnel.length-1&&<i/>}</Link>)}</div>:<div className="loading">暂无真实漏斗数据</div>}</section>
  <section className="panel"><div className="panel-head"><div><span className="eyebrow">优先候选队列</span><h2>今日候选</h2></div><Link to="/candidates">全部候选 <ExternalLink size={13}/></Link></div>{data.candidates.length?<div className="data-table"><table><thead><tr><th>股票</th><th>状态</th><th>评分</th><th>高度模型</th><th>高度排名</th><th>市场最高</th><th>竞价量比</th><th>盘中</th></tr></thead><tbody>{data.candidates.map(c=><tr key={c.symbol}><td><Link className="stock" to={`/stock/${c.symbol}`}><b>{c.symbol}</b><span>{c.name}</span></Link></td><td><StatusBadge status={c.status}/></td><td><strong>{c.score}</strong><small>/100 · {c.grade}级</small></td><td>{c.board_height}板<small>{c.sub_strategy}</small></td><td>第{c.height_rank}档</td><td>{c.market_highest?'是':'否'}</td><td className="mono">{c.auction_volume_ratio.toFixed(2)}倍</td><td><StatusBadge status={c.intraday_status}/></td></tr>)}</tbody></table></div>:<div className="loading">暂无真实候选数据</div>}</section>
 </div>;
}
