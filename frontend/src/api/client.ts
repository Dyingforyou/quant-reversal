import type {Candidate,DecisionTrace,PipelineRecord} from '../types';

type Progress={stage:string;latest:string;next:string;updated_at:string;status:'running'|'waiting'|'error'};
type DashboardData={progress:Progress;kpis:[string,string,string][];funnel:[string,number][];candidates:Candidate[]};
const emptyDashboard:DashboardData={
 progress:{stage:'等待数据',latest:'尚未取得真实执行进展',next:'等待下一次定时任务',updated_at:'—',status:'waiting'},
 kpis:[['全市场股票','—','等待真实数据'],['可交易股票','—','等待真实数据'],['基础候选','—','等待真实数据'],['竞价候选','—','等待真实数据'],['盘中触发','—','等待真实数据'],['实际买入','—','未接入交易'],['当前持仓','—','未接入交易'],['今日策略收益','—','未计算']],
 funnel:[],candidates:[]
};
async function json<T>(name:string,fallback:T):Promise<T>{
 try{const response=await fetch(`/quant-reversal/data/${name}.json`,{cache:'no-store'});if(!response.ok)return fallback;return await response.json() as T}catch{return fallback}
}
const noDecision=(symbol:string):DecisionTrace=>({trade_date:'—',symbol,name:'暂无真实数据',strategy_version:'v0.2.0',config_version:'real',decision_id:'—',run_id:'—',final_status:'NO_DATA',current_stage:'等待数据',total_score:null,max_score:100,primary_reason:'尚未生成该股票的真实决策记录',board_height:0,height_group:'—',height_rank:0,market_highest:false,sub_strategy:'—',model_route_reason:'尚未路由',stages:[],signal:null,order:null,position:null});
export const api={
 dashboard:()=>json<DashboardData>('dashboard',emptyDashboard),
 pipeline:()=>json<PipelineRecord[]>('pipeline',[]),
 candidates:()=>json<Candidate[]>('candidates',[]),
 decision:(symbol:string)=>json<DecisionTrace>(`decision-${symbol}`,noDecision(symbol)),
};
