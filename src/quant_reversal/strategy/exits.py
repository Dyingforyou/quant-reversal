from datetime import date
def can_exit(entry_date:date,current_date:date)->bool:return current_date>entry_date
def exit_reason(return_pct:float,minute:str,holding_days:int,stop:float=-.05,take:float=.08,max_days:int=3)->str|None:
    if return_pct<=stop:return "STOP" 
    if return_pct>=take:return "TAKE_PROFIT"
    if holding_days>=max_days:return "MAX_HOLDING"
    if minute=="10:00":return "NEXT_DAY_1000"
    return None

