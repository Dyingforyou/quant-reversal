from datetime import datetime
from pathlib import Path
import hashlib,json,subprocess,yaml
def create_run(output:Path,mode:str,config:dict,date_range:list[str])->Path:
    run_id=datetime.now().strftime("%Y%m%d_%H%M%S_%f")+"_"+mode;root=output/run_id;root.mkdir(parents=True)
    text=yaml.safe_dump(config,allow_unicode=True,sort_keys=True);(root/"config.yaml").write_text(text,encoding="utf-8")
    try:git=subprocess.run(["git","rev-parse","HEAD"],capture_output=True,text=True,check=False).stdout.strip() or None
    except OSError:git=None
    manifest={"run_id":run_id,"mode":mode,"date_range":date_range,"config_hash":hashlib.sha256(text.encode()).hexdigest(),"data_files":{},"git_commit":git,"started_at":datetime.now().isoformat()}
    (root/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8");return root

