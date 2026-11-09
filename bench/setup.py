from __future__ import annotations
import hashlib
import json
import secrets
import shutil
from datetime import datetime,timezone
from pathlib import Path
from .dataset import make_dataset
from .prompts import roles_for

NUMBER_WORDS={2:'two',3:'three',4:'four',5:'five',6:'six',7:'seven',8:'eight',9:'nine',10:'ten',11:'eleven',12:'twelve'}

ROOT=Path(__file__).resolve().parents[1]
def utc(): return datetime.now(timezone.utc).isoformat()

def run_roles(run):
    """Agent IDs for a run (team size is fixed at setup)."""
    cfg=json.loads((Path(run)/'operator'/'run_config.json').read_text())
    return roles_for(int(cfg.get('agents',4)))


def run_task(run):
    f=Path(run)/'operator'/'run_config.json'
    return json.loads(f.read_text()).get('task','ml') if f.exists() else 'ml'


def create(run_path,seed=731,force=False,agents=4,chess=False,chess_key=None,chess_fixture=False):
    roles_for(agents)  # validates the team size
    run=Path(run_path).resolve()
    if run.exists() and any(run.iterdir()):
        if not force: raise FileExistsError(f'{run} exists; use a new run path or --force')
        shutil.rmtree(run)
    if chess:
        return create_chess(run,seed=seed,agents=agents,key_path=chess_key,fixture=chess_fixture)
    workspace=run/'workspace'; private=run/'operator'
    shutil.copytree(ROOT/'agent_project', workspace)
    private.mkdir(parents=True)
    # Workspace docs state the team size; forced-message wording is gone (messages are voluntary).
    word=NUMBER_WORDS[agents]
    for doc,old in (('README.md','for four agents'),('shared/README.md','All four agents')):
        f=workspace/doc
        text=f.read_text()
        text=text.replace(old,old.replace('four',word)).replace(' Your instructions say which team messages are required.','')
        f.write_text(text)
    (workspace/'data').mkdir(exist_ok=True)
    (workspace/'artifacts').mkdir(exist_ok=True)
    train,dev,holdout=make_dataset(seed=seed)
    train.to_csv(workspace/'data'/'train.csv',index=False)
    dev.drop(columns=['incident_72h']).to_csv(workspace/'data'/'dev.csv',index=False)
    holdout.drop(columns=['incident_72h']).to_csv(private/'holdout_features.csv',index=False)
    dev[['row_id','incident_72h']].to_csv(private/'dev_labels.csv',index=False)
    holdout[['row_id','incident_72h']].to_csv(private/'holdout_labels.csv',index=False)
    (private/'events.jsonl').touch();(private/'reasoning.jsonl').touch()
    (private/'reports.jsonl').touch();(private/'adjudications.jsonl').touch()
    signature=hashlib.sha256((workspace/'README.md').read_bytes()).hexdigest()
    (private/'run_config.json').write_text(json.dumps({'seed':seed,'created_at':utc(),
        'template_sha256':signature,'incident_ids':[],'api_requests':0,'agents':agents},indent=2))
    return run


def create_chess(run,seed=731,agents=12,key_path=None,fixture=False):
    """Chess Decision Challenge workspace. The answer key stays in operator/."""
    from .chess_key import load_key_file,fixture_key,public_positions
    if bool(key_path)==bool(fixture):
        raise ValueError('chess setup needs exactly one of --chess-key-from FILE or --chess-fixture')
    from .chess_eval import init_state
    key=fixture_key(seed=seed) if fixture else load_key_file(key_path)
    n=len(key['positions'])
    if n!=36:
        raise ValueError(f'the two-stage chess assessment uses exactly 36 positions (key has {n})')
    workspace=run/'workspace'; private=run/'operator'
    shutil.copytree(ROOT/'agent_project_chess',workspace)
    private.mkdir(parents=True)
    (workspace/'shared'/'submissions').mkdir(parents=True,exist_ok=True)
    (workspace/'positions.json').write_text(json.dumps(public_positions(key),indent=2)+'\n')
    (private/'chess_answer_key.json').write_text(json.dumps(key,indent=2))
    init_state(private/'chess_gateway')
    for name in ('events.jsonl','reasoning.jsonl','reports.jsonl','adjudications.jsonl'):
        (private/name).touch()
    signature=hashlib.sha256((workspace/'README.md').read_bytes()).hexdigest()
    (private/'run_config.json').write_text(json.dumps({'seed':seed,'created_at':utc(),
        'template_sha256':signature,'incident_ids':[],'api_requests':0,'agents':agents,
        'task':'chess','chess_positions':n,'chess_key_source':key['source'],
        'chess_key_artificial':bool(key.get('artificial'))},indent=2))
    return run
