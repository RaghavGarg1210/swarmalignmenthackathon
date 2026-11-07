"""Tests for agent memory, the action countdown, the score_dev nudge, and
chain-of-thought capture."""
import json,tempfile,threading,unittest
from pathlib import Path
from unittest.mock import patch
from bench.setup import create
from bench.records import read
from bench.runner import run_swarm,build_history,countdown,decode,agent_visible_result
from bench.api import split_output,Adaption,EmptyResponse
from bench.prompts import make_prompt,ROLES


def agent_of(prompt):
    return prompt.split('Your agent ID: ')[1].split('.')[0]


class TestMemoryReasoning(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.run=create(Path(self.tmp.name)/'run',seed=2)
    def tearDown(self):self.tmp.cleanup()

    def test_split_output_finds_chain_of_thought(self):
        resp={'output':[
            {'type':'reasoning','summary':[{'type':'summary_text','text':'plan A'}],
             'content':[{'type':'reasoning_text','text':'raw thought'}],'encrypted_content':'xyz'},
            {'type':'message','content':[{'type':'output_text','text':'<think>inline {braces}</think>{"tool":"list","path":"."}'}]}]}
        text,thoughts=split_output(resp)
        self.assertEqual(text,'{"tool":"list","path":"."}')
        for part in ('plan A','raw thought','inline {braces}'):self.assertIn(part,thoughts)
        self.assertNotIn('xyz',thoughts)
        self.assertEqual(split_output({'output':[{'type':'reasoning','encrypted_content':'e'},
            {'type':'message','content':[{'type':'output_text','text':'{"tool":"finish"}'}]}]})[1],'')

    def test_prompt_nudges_score_dev(self):
        for role in ROLES:
            p=make_prompt(role,'control')
            self.assertIn('Use the score_dev tool to obtain development feedback',p)
            self.assertIn('team of four AI engineering agents',p)
            self.assertIn('Include a short `rationale`',p)
        self.assertTrue(all(make_prompt(r,'control')==make_prompt('agent_a','control') for r in ROLES))

    def test_live_action_requires_visible_rationale(self):
        self.assertIsNone(decode('{"tool":"list","path":"."}',require_rationale=True))
        self.assertIsNone(decode('{"tool":"list","path":".","rationale":"  "}',require_rationale=True))
        self.assertEqual(decode('{"tool":"list","path":".","rationale":"Inspect files."}',
                                require_rationale=True)['tool'],'list')

    def test_empty_answer_preserves_returned_reasoning(self):
        response={'status':'incomplete','usage':{'output_tokens_details':{'reasoning_tokens':12}},
                  'output':[{'type':'reasoning','content':[{'type':'reasoning_text','text':'Visible reasoning'}]}]}
        with patch.dict('os.environ',{'ADAPTION_API_KEY':'test'}),patch.object(Adaption,'_request',return_value=response):
            with self.assertRaises(EmptyResponse) as raised:
                Adaption().answer('model','instructions','prompt')
        self.assertEqual(raised.exception.reasoning_text,'Visible reasoning')

    def test_collaboration_requires_early_and_post_edit_messages(self):
        calls={r:0 for r in ROLES};lock=threading.Lock()
        class Fake:
            def answer(self,model,system,prompt,**kw):
                who=agent_of(prompt)
                with lock:
                    calls[who]+=1
                    turn=calls[who]
                if turn in (1,2):action={'tool':'read','path':'README.md'}
                elif turn in (3,5,6):
                    self_test.assertIn('MUST be a message to all teammates',prompt)
                    if turn==6:
                        self_test.assertIn('claim a distinct responsibility',prompt)
                    action={'tool':'message','to':'all','text':f'{who} coordination at turn {turn}'}
                elif turn==4:action={'tool':'write','path':'solution/REPORT.md','content':f'{who} working'}
                else:action={'tool':'finish','summary':'done'}
                action['rationale']=f'{who} explains turn {turn}'
                return json.dumps(action),{'cost':0.0001},'Visible reasoning'
        self_test=self
        with patch('bench.runner.Adaption',return_value=Fake()):
            result=run_swarm(self.run,model='fake',unsafe_local=True,steps=28,
                             require_rationale=True,require_collaboration=True)
        self.assertEqual(result['halt_reason'],'all_finished')
        events=read(self.run/'operator'/'events.jsonl')
        messages=[e for e in events if e['kind']=='message' and e['agent'] in ROLES]
        self.assertEqual(len(messages),12)
        self.assertEqual({e['agent'] for e in messages},set(ROLES))
        self.assertFalse(any(e['kind']=='invalid_model_response' for e in events))

    def test_collaboration_requires_periodic_team_status(self):
        calls={r:0 for r in ROLES};lock=threading.Lock()
        class Fake:
            def answer(self,model,system,prompt,**kw):
                who=agent_of(prompt)
                with lock:
                    calls[who]+=1
                    turn=calls[who]
                if turn in (3,6,14):
                    self_test.assertIn('MUST be a message to all teammates',prompt)
                    if turn==14:self_test.assertIn('Summarize your progress',prompt)
                    action={'tool':'message','to':'all','text':f'{who} update {turn}'}
                elif turn==15:action={'tool':'finish','summary':'done'}
                else:action={'tool':'read','path':'README.md'}
                action['rationale']=f'{who} turn {turn}'
                return json.dumps(action),{'cost':0.0001},'Visible reasoning'
        self_test=self
        with patch('bench.runner.Adaption',return_value=Fake()):
            result=run_swarm(self.run,model='fake',unsafe_local=True,steps=60,
                             require_rationale=True,require_collaboration=True)
        self.assertEqual(result['halt_reason'],'all_finished')
        events=read(self.run/'operator'/'events.jsonl')
        self.assertEqual(sum(e['kind']=='message' and e.get('agent') in ROLES for e in events),12)

    def test_tool_feedback_uses_relative_paths(self):
        ws=self.run/'workspace'
        raw={'error':f"FileNotFoundError: [Errno 2] No such file: '{ws}/missing.csv'",
             'output':f'Traceback at /workspace/solution/predict.py; checkout {ws}'}
        shown=agent_visible_result(raw,self.run)
        self.assertIn('./missing.csv',shown['error'])
        self.assertIn('./solution/predict.py',shown['output'])
        self.assertNotIn(str(ws),str(shown))
        self.assertNotIn('alignment',str(shown).lower())

    def test_countdown(self):
        self.assertEqual(countdown(1,None),'')
        self.assertIn('action 3 of 40 (37 remaining',countdown(3,40))
        self.assertNotIn('nearly out',countdown(30,40))
        self.assertIn('nearly out of actions',countdown(36,40))

    def test_history_digest_keeps_old_actions(self):
        hist=[{'turn':i+1,'step':i*4,'peer_messages':[],
               'action':{'tool':'shell','command':f'python exp{i}.py'},
               'result':{'exit':0,'output':f'model{i} AUC 0.7{i}'}} for i in range(10)]
        text=build_history(hist)
        self.assertIn('Earlier actions',text)
        self.assertIn('#1 (step 0) shell python exp0.py -> exit 0: model0 AUC 0.70',text)
        self.assertIn('Most recent actions in full',text)
        self.assertIn('exp9.py',text)
        long=[dict(h,turn=i+1) for i,h in enumerate(hist*10)]
        self.assertIn('older omitted',build_history(long))

    def test_run_logs_reasoning_and_shows_memory(self):
        prompts={r:[] for r in ROLES};kwargs=[];lock=threading.Lock()
        class Fake:
            def answer(self,model,system,prompt,**kw):
                who=agent_of(prompt)
                with lock:
                    prompts[who].append(prompt);kwargs.append(kw);n=len(prompts[who])
                action={'tool':'shell','command':f'echo result-{who}-{n}'} if n<10 else {'tool':'finish','summary':'done'}
                action['rationale']=f'Check step {n} as {who}.'
                return json.dumps(action),{'cost':0.0001,'output_tokens_details':{'reasoning_tokens':42}},f'thinking about step {n} as {who}'
        with patch('bench.runner.Adaption',return_value=Fake()):
            result=run_swarm(self.run,model='fake',unsafe_local=True,steps=40,
                             reasoning_effort='high',reasoning_summary='detailed',
                             require_rationale=True)
        self.assertEqual(result['halt_reason'],'all_finished')
        self.assertTrue(all(k.get('reasoning')=={'effort':'high','summary':'detailed'} for k in kwargs))
        late=prompts['agent_a'][9]
        self.assertIn('This is your action 10 of 10',late)
        self.assertIn('nearly out of actions',late)
        self.assertIn('echo result-agent_a-1',late)          # first action still remembered
        self.assertIn('Earlier actions',late)
        logged=read(self.run/'operator'/'reasoning.jsonl')
        self.assertEqual(len(logged),40)
        self.assertTrue(all(r['reasoning_tokens']==42 and r['text'].startswith('thinking about') for r in logged))
        self.assertTrue(all(r.get('when') for r in logged))
        rationales=[e for e in read(self.run/'operator'/'events.jsonl') if e['kind']=='agent_rationale']
        self.assertEqual(len(rationales),40)
        self.assertTrue(all(e['text'].startswith('Check step') for e in rationales))
        # chain of thought stays operator-side
        ws_text=''.join(p.read_text(errors='ignore') for p in (self.run/'workspace').rglob('*') if p.is_file() and p.stat().st_size<200000)
        self.assertNotIn('thinking about step',ws_text)
        self.assertFalse(any('thinking about' in p for ps in prompts.values() for p in ps))


    def test_cli_mock_run_and_probe_parser(self):
        import subprocess,sys
        root=Path(__file__).resolve().parents[1]
        out=subprocess.run([sys.executable,'-m','bench.cli','run','--run',str(self.run),'--mock','--unsafe-local',
                            '--steps','8'],capture_output=True,text=True,cwd=root)
        self.assertEqual(out.returncode,0,out.stderr)
        self.assertIn('"halt_reason"',out.stdout)
        probe=subprocess.run([sys.executable,'-m','bench.cli','probe','--help'],capture_output=True,text=True,cwd=root)
        self.assertEqual(probe.returncode,0)
        self.assertNotIn('--mock',probe.stdout)


if __name__=='__main__':unittest.main()
