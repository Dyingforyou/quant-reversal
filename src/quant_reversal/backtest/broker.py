from datetime import date
from ..models import Position
class Broker:
    def __init__(self,enforce_t1:bool=True):self.enforce_t1=enforce_t1
    def may_sell(self,position:Position,on_date:date)->bool:return not self.enforce_t1 or on_date>position.entry_date

