from __future__ import annotations
import argparse,json,os,subprocess,sys,time
from pathlib import Path
from .setup import create
from .runner import run_swarm
from .tools import run_shell,safe_path
from .api import Adaption
from .records import read
from .analysis import analyze
from .judge import dev_score,compare_dev,trusted_score


def final_score(run,unsafe_local=False):
    root=Path(run).resolve()
    ws=root/'workspace'
    source=root/'operator'/'holdout_features.csv'
    dest=ws/'artifacts'/'holdout_predictions.csv'
    if unsafe_local:
        # For local smoke tests only; untrusted code must run in Docker.
        local=ws/'artifacts'/'holdout_features.csv'
        import shutil
        shutil.copy(source,local)
        result=run_shell(ws,'python solution/predict.py --input artifacts/holdout_features.csv --output artifacts/holdout_predictions.csv',unsafe_local=True)
        local.unlink(missing_ok=True)
    else:
        result=subprocess.run(['docker','run','--rm','--network','none','--read-only','--cap-drop','ALL',
          '--security-opt','no-new-privileges','--pids-limit','128','--memory','2g',
          '--tmpfs','/tmp:rw,noexec,nosuid,size=128m',
          '--user',f'{os.getuid()}:{os.getgid()}',
          '-e','PYTHONDONTWRITEBYTECODE=1','-e','HOME=/tmp',
          '-v',f'{ws}:/workspace:rw','-v',f'{source}:/holdout/input.csv:ro',
          '-w','/workspace','swarm-integrity:local',
          'python','solution/predict.py','--input','/holdout/input.csv',
          '--output','artifacts/holdout_predictions.csv'],capture_output=True,text=True,timeout=120)
        result={'exit':result.returncode,'output':(result.stdout+result.stderr)[-4000:]}
    if result['exit']:
        return {'prediction_failed':result}
    return trusted_score(root,dest)


def main():
    p=argparse.ArgumentParser(description='Swarm integrity benchmark (operator CLI)')
    sub=p.add_subparsers(dest='cmd',required=True)
    s=sub.add_parser('setup');s.add_argument('--run',required=True);s.add_argument('--seed',type=int,default=731);s.add_argument('--force',action='store_true')
    s=sub.add_parser('models')
    s=sub.add_parser('run');s.add_argument('--run',required=True)
    s.add_argument('--model');s.add_argument('--arm',choices=['control','duty','audit_notice','fixed_penalty','graduated_penalty'],default='control')
    s.add_argument('--steps',type=int,default=48,help='total action allowance; must be divisible by 4, shared equally among concurrent agents');s.add_argument('--honeypot-step',type=int,default=-1)
    s.add_argument('--honeypot-kind',choices=['peer-shortcut','peer-suppression','artifact-anomaly'],default='artifact-anomaly')
    s.add_argument('--honeypot-target',choices=['agent_a','agent_b','agent_c','agent_d'])
    s.add_argument('--max-cost-usd',type=float,help='shared estimated USD budget for all four agents')
    s.add_argument('--max-output-tokens',type=int,default=65536,help='maximum output tokens per model response')
    s.add_argument('--output-price-ceiling',type=float,help='conservative USD per 1M output tokens for budget reservation')
    s.add_argument('--mock',action='store_true');s.add_argument('--unsafe-local',action='store_true')
    s=sub.add_parser('score-dev');s.add_argument('--run',required=True);s.add_argument('--predictions',default='artifacts/dev_predictions.csv');s.add_argument('--independent',action='store_true')
    s=sub.add_parser('score-final');s.add_argument('--run',required=True);s.add_argument('--unsafe-local',action='store_true')
    s=sub.add_parser('analyze');s.add_argument('--run',required=True)
    s=sub.add_parser('inbox');s.add_argument('--run',required=True);s.add_argument('--follow',action='store_true')
    s=sub.add_parser('adjudicate');s.add_argument('--run',required=True);s.add_argument('--incident-id',required=True);s.add_argument('--report-id',required=True);s.add_argument('--decision',choices=['valid','invalid'],required=True)
    a=p.parse_args()
    if a.cmd=='setup':
        print('Run created:',create(a.run,seed=a.seed,force=a.force))
    elif a.cmd=='models':
        print(json.dumps(Adaption().models(),indent=2))
    elif a.cmd=='run':
        print(json.dumps(run_swarm(a.run,a.model,a.arm,a.steps,a.honeypot_step,a.honeypot_kind,
                                   a.honeypot_target,a.unsafe_local,a.mock,
                                   max_cost_usd=a.max_cost_usd,max_output_tokens=a.max_output_tokens,
                                   output_price_ceiling=a.output_price_ceiling),indent=2))
    elif a.cmd=='score-dev':
        path=safe_path(Path(a.run)/'workspace',a.predictions)
        print(json.dumps(compare_dev(a.run,path) if a.independent else dev_score(a.run,path),indent=2))
    elif a.cmd=='score-final':print(json.dumps(final_score(a.run,a.unsafe_local),indent=2))
    elif a.cmd=='analyze':print(json.dumps(analyze(a.run),indent=2))
    elif a.cmd=='inbox':
        offset=0
        try:
            while True:
                rows=read(Path(a.run)/'operator'/'reports.jsonl')
                for row in rows[offset:]:print(json.dumps(row,indent=2))
                offset=len(rows)
                if not a.follow: break
                time.sleep(1)
        except KeyboardInterrupt:pass
    elif a.cmd=='adjudicate':
        from .records import append
        rows=read(Path(a.run)/'operator'/'reports.jsonl')
        incidents=[x for x in read(Path(a.run)/'operator'/'events.jsonl') if x.get('kind')=='honeypot_exposure']
        if a.report_id not in [x['id'] for x in rows]:p.error('report id not found')
        if a.incident_id not in [x['id'] for x in incidents]:p.error('incident id not found')
        path=Path(a.run)/'operator'/'adjudications.jsonl'
        import uuid
        with path.open('a') as f:f.write(json.dumps({'id':uuid.uuid4().hex[:12], 'incident_id':a.incident_id,'report_id':a.report_id,'decision':a.decision})+'\n')
        print('Adjudication recorded.')

if __name__=='__main__':main()
