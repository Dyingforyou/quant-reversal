from pathlib import Path
import pandas as pd
def write_html(tables:dict[str,pd.DataFrame],path:Path,title:str="量化反包研究报告"):
    path.parent.mkdir(parents=True,exist_ok=True);body="".join(f"<h2>{name}</h2>{df.to_html(index=False)}" for name,df in tables.items());path.write_text(f"<html><meta charset='utf-8'><body><h1>{title}</h1>{body}</body></html>",encoding="utf-8")

