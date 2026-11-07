from __future__ import annotations
import hashlib
import json
import secrets
import shutil
from datetime import datetime,timezone
from pathlib import Path
from .dataset import make_dataset

ROOT=Path(__file__).resolve().parents[1]
def utc(): return datetime.now(timezone.utc).isoformat()

def create(run_path,seed=731,force=False):
    run=Path(run_path).resolve()
    if run.exists() and any(run.iterdir()):
        if not force: raise FileExistsError(f'{run} exists; use a new run path or --force')
        shutil.rmtree(run)
    workspace=run/'workspace'; private=run/'operator'
    shutil.copytree(ROOT/'agent_project', workspace)
    private.mkdir(parents=True)
    (workspace/'data').mkdir(exist_ok=True)
    (workspace/'artifacts').mkdir(exist_ok=True)
    train,dev,holdout=make_dataset(seed=seed)
    train.to_csv(workspace/'data'/'train.csv',index=False)
    dev.drop(columns=['incident_72h']).to_csv(workspace/'data'/'dev.csv',index=False)
    holdout.drop(columns=['incident_72h']).to_csv(private/'holdout_features.csv',index=False)
    dev[['row_id','incident_72h']].to_csv(private/'dev_labels.csv',index=False)
    holdout[['row_id','incident_72h']].to_csv(private/'holdout_labels.csv',index=False)
    (private/'events.jsonl').touch();(private/'reports.jsonl').touch();(private/'adjudications.jsonl').touch()
    signature=hashlib.sha256((workspace/'README.md').read_bytes()).hexdigest()
    (private/'run_config.json').write_text(json.dumps({'seed':seed,'created_at':utc(),
        'template_sha256':signature,'incident_ids':[],'api_requests':0},indent=2))
    return run
