from pathlib import Path
import pandas as pd
def write_scan(frame:pd.DataFrame,out_dir:Path)->dict:
    out_dir.mkdir(parents=True,exist_ok=True);csv=out_dir/"candidates.csv";pq=out_dir/"candidates.parquet";html=out_dir/"report.html"
    frame.to_csv(csv,index=False);frame.to_parquet(pq,index=False);html.write_text("<html><meta charset='utf-8'><body><h1>量化反包候选</h1>"+frame.to_html(index=False)+"</body></html>",encoding="utf-8")
    return {"csv":str(csv),"parquet":str(pq),"html":str(html)}

