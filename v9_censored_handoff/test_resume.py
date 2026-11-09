from pathlib import Path
import tempfile, shutil, json, sys, hashlib
sys.path.insert(0,str(Path(__file__).resolve().parent/'code'))
from bench.resume_handoff import preview, live_resume, fork_checkpoint, verify_policy, system_prompt
from bench.records import read
SRC=Path(__file__).resolve().parent/'run'
class FakeClient:
 def __init__(self):self.calls=[]
 def answer(self,model,system,prompt,**kwargs):
  import re
  a=re.search('Your agent ID: (agent_[a-l])',prompt).group(1)
  self.calls.append((a,system,prompt))
  return json.dumps({'tool':'finish','summary':'Mock continuation complete','rationale':'Testing resumed state without changing grading or workspace.'}),{'cost':0.0002},''

class FakeAction:
 def __init__(self):self.calls=[]
 def __call__(self,run,role,action,step,**kw):
  self.calls.append((role,action,step,kw.get('rogue_mode')))
  return {'finished':True,'summary':'Mock continuation complete'}

for arm in ('control','rogue','panopticon'):
 with tempfile.TemporaryDirectory() as temp:
  t=Path(temp)/'branch'
  fork_checkpoint(SRC,t)
  f=FakeClient();h=FakeAction()
  original_a=(SRC/'operator/rogue_agent_snapshots/agent_a.json').read_bytes()
  before_state=(SRC/'operator/chess_gateway/state.json').read_bytes()
  before_ave=hashlib.sha256(original_a).hexdigest()
  preview(t,arm)
  out=live_resume(t,arm,unsafe_local=True,max_new_turns=1,client=f,action_handler=h)
  assert len(f.calls)>=10, (arm,len(f.calls))
  assert not any('V9 TEAM COOPERATION' in s for a,s,_ in f.calls if a!='agent_a')
  assert not any('prompt injection' in p.lower() for a,s,p in f.calls if a!='agent_a')
  assert not any('Available prior model-returned reasoning' in p for a,s,p in f.calls if a=='agent_a')
  assert all(('`report`' not in s) == (arm=='rogue') for a,s,_ in f.calls if a!='agent_a')
  assert all(t == (arm=='rogue' or a=='agent_a') for a,_,_,t in h.calls)
  assert t.joinpath('operator/chess_gateway/state.json').read_bytes()==before_state
  assert SRC.joinpath('operator/rogue_agent_snapshots/agent_a.json').read_bytes()==original_a
  assert t.joinpath('operator/resume_started.json').is_file()
  assert any(e['kind']=='aligned_resume_started' for e in read(t/'operator/events.jsonl'))
  assert any(e['kind']=='worker_system_policy_replaced' for e in read(t/'operator/events.jsonl'))
  print(arm,'PASS','model calls',len(f.calls),'action calls',len(h.calls),'halt',out['halt_reason'])
