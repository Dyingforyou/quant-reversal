import type {RuleStatus} from '../types';
const labels:Record<string,string>={PASS:'通过',FAIL:'失败',NOT_RUN:'未执行',NO_DATA:'无数据',ERROR:'异常','BUY SIGNAL':'买入信号',FILLED:'已成交',TRIGGERED:'已触发',OPEN:'持仓中',WATCH:'观察',WAITING:'等待确认',REJECT:'已淘汰',CLOSED:'已平仓'};
export const statusLabel=(status:string)=>labels[status]??status;
export function StatusBadge({status}:{status:string}){return <span className={`status status-${status.toLowerCase().replaceAll(' ','-').replaceAll('_','-')}`}>{statusLabel(status)}</span>}
export function StageDot({status}:{status:RuleStatus|string}){return <span className={`stage-dot dot-${status.toLowerCase()}`} aria-label={status}/>}
