"""Startup and chess submission permissions, using a fake grader to stay offline.

These tests intentionally do not need Stockfish or python-chess. The normal
chess tests still cover the actual scoring engine where dependencies exist.
"""
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from bench.prompts import make_prompt
from bench.records import read
from bench.runner import run_swarm
from bench.tools import chess_official, perform


class FakeGateway:
    def shutdown(self): pass
    def server_close(self): pass


def fake_services():
    gateway=types.ModuleType('bench.chess_gateway')
    gateway.start_local=lambda *args:FakeGateway()
    evaluation=types.ModuleType('bench.chess_eval')
    evaluation.load_key=lambda run:{'positions':[]}
    evaluation.state_dir=lambda run:Path(run)/'operator'/'state'
    evaluation.snapshots_dir=lambda run:Path(run)/'operator'/'snapshots'
    return {'bench.chess_gateway':gateway,'bench.chess_eval':evaluation}


class ChessCoordinationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)/'run'
        (self.root/'operator').mkdir(parents=True)
        (self.root/'workspace'/'shared').mkdir(parents=True)
        (self.root/'workspace'/'solution').mkdir(parents=True)
        (self.root/'workspace'/'README.md').write_text('Chess task\n')
        (self.root/'operator'/'run_config.json').write_text(json.dumps({
            'task':'chess','agents':12,'chess_positions':36}))
        for filename in ('events.jsonl','reasoning.jsonl','reports.jsonl'):
            (self.root/'operator'/filename).touch()

    def tearDown(self):
        self.tmp.cleanup()

    def test_delegation_happens_before_every_teammate_first_turn(self):
        with patch.dict(sys.modules,fake_services()):
            out=run_swarm(self.root,mock=True,unsafe_local=True,steps=12)
        events=read(self.root/'operator'/'events.jsonl')
        complete_index=next(i for i,e in enumerate(events) if e['kind']=='delegation_complete')
        member_indexes=[i for i,e in enumerate(events) if e['kind']=='turn_started' and e.get('agent')!='agent_a']
        self.assertEqual(len(member_indexes),11)
        self.assertTrue(all(i>complete_index for i in member_indexes))
        self.assertEqual(out['halt_reason'],'action_allowance_reached')
        assignment=json.loads((self.root/'workspace'/'shared'/'assignments.json').read_text())['assignments']
        self.assertEqual(len(assignment),12)
        self.assertEqual(set(assignment),{f'agent_{letter}' for letter in 'abcdefghijkl'})
        messages=[e for e in events if e['kind']=='message' and e.get('delegation_id')]
        self.assertEqual(len(messages),1)
        self.assertEqual(messages[0]['agent'],'agent_a')
        self.assertEqual(messages[0]['to'],'all')

    def test_no_delegation_prevents_other_agents_starting(self):
        def never_delegate(role,turn,messages,*args,**kwargs):
            return {'tool':'finish','summary':'I am finished'}
        with patch.dict(sys.modules,fake_services()),patch('bench.runner.mock_answer',side_effect=never_delegate):
            out=run_swarm(self.root,mock=True,unsafe_local=True,steps=12)
        events=read(self.root/'operator'/'events.jsonl')
        self.assertEqual(out['halt_reason'],'delegation_not_completed')
        self.assertFalse(any(e['kind']=='turn_started' and e.get('agent')!='agent_a' for e in events))

    def test_only_agent_a_may_delegate_and_submit(self):
        tasks={f'agent_{letter}':f'Analyze assigned position group {letter} and post results.' for letter in 'abcdefghijkl'}
        denied=perform(self.root,'agent_b',{'tool':'delegate','assignments':tasks},1)
        self.assertIn('Only agent_a',denied['error'])
        denied=perform(self.root,'agent_b',{'tool':'score_dev'},2)
        self.assertIn('Only Agent A',denied['error'])
        self.assertIn('Only Agent A',chess_official(self.root,'agent_b',3)['error'])
        bad=perform(self.root,'agent_a',{'tool':'delegate','assignments':{'agent_a':'Integrate board'}},4)
        self.assertIn('error',bad)
        good=perform(self.root,'agent_a',{'tool':'delegate','assignments':tasks},5)
        self.assertTrue(good['delegated'])
        self.assertFalse(any(e['kind']=='chess_official_grade' for e in read(self.root/'operator'/'events.jsonl')))

    def test_role_prompts_and_example(self):
        a=make_prompt('agent_a','control',task='chess',n_agents=12)
        b=make_prompt('agent_b','control',task='chess',n_agents=12)
        self.assertIn('Deciding when to submit is your responsibility',a)
        self.assertIn('you cannot submit either stage',b)
        self.assertIn('Only Agent A can submit either stage',a)
        example=a.split('Example:\n')[1].split('\n\nUse `message`')[0]
        parsed=json.loads(example)
        self.assertEqual(len(parsed['assignments']),12)
        self.assertEqual(parsed['tool'],'delegate')
        self.assertNotIn('Additional Reporting Requirements',a)
        self.assertIn('Additional Reporting Requirements',make_prompt('agent_a','panopticon',task='chess',n_agents=12))


if __name__=='__main__':
    unittest.main()
