import {Construction} from 'lucide-react';
const names:Record<string,string>={trades:'交易记录',sectors:'板块强度',research:'因子研究',backtest:'策略回测',runs:'运行记录',config:'参数配置'};
export default function Placeholder({page}:{page:string}){return <div className="page"><div className="page-title"><div><span className="eyebrow">模块预览</span><h1>{names[page]??page}</h1></div></div><section className="panel empty"><Construction/><h2>模块将在下一阶段接入</h2><p>当前版本优先交付今日总览、筛选流水与决策审计核心链路。</p></section></div>}
