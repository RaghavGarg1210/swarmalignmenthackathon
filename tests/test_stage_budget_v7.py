"""Chess staged-compute prompt and configuration regression tests."""
import tempfile
import unittest
import json
import sys
from pathlib import Path
from unittest.mock import patch

from bench.prompts import make_prompt
from bench.runner import chess_stage_budget_status, run_swarm
from bench.setup import create
from bench.records import read
from bench.tools import perform
from tests.test_chess_coordination import fake_services


class TestStagedChessBudget(unittest.TestCase):
    def test_coordinator_and_member_are_told_stage_limits(self):
        for role in ('agent_a', 'agent_d'):
            prompt=make_prompt(role, 'control', task='chess', n_agents=12)
            for amount in ('$1.40', '$2.60', '$4.00'):
                self.assertIn(amount, prompt)
        self.assertIn('Your official Stage 1 submission unlocks',
                      make_prompt('agent_a', 'control', task='chess', n_agents=12))

    def test_chess_rejects_different_configured_total(self):
        with tempfile.TemporaryDirectory() as tmp:
            run=create(Path(tmp)/'run', seed=42, agents=12)
            with patch('bench.setup.run_task', return_value='chess'):
                with self.assertRaisesRegex(ValueError,'Chess staged budget requires'):
                    run_swarm(run, mock=True, unsafe_local=True, steps=12, team_budget_usd=2.0)

    def test_each_stage_shows_its_current_remaining_budget(self):
        first=chess_stage_budget_status(0.75,1.40,0)
        second=chess_stage_budget_status(0.75,4.00,1)
        self.assertIn('Current Stage 1 remaining: $0.650 of $1.400',first)
        self.assertIn('$2.600 Stage 2 allocation unlocks',first)
        self.assertIn('Current Stage 2 remaining: $3.250',second)
        self.assertIn('any unused Stage 1 budget',second)

    def test_budget_exhaustion_auto_submits_both_stages(self):
        with tempfile.TemporaryDirectory() as tmp:
            run=Path(tmp)/'run'
            (run/'operator').mkdir(parents=True)
            (run/'workspace'/'shared').mkdir(parents=True)
            (run/'workspace'/'solution').mkdir(parents=True)
            (run/'operator'/'run_config.json').write_text(json.dumps({
                'task':'chess','agents':12,'chess_positions':36}))
            for name in ('events.jsonl','reasoning.jsonl','reports.jsonl'):
                (run/'operator'/name).touch()
            class Client:
                def answer(self,model,system,prompt,**kwargs):
                    agent=prompt.split('Your agent ID: ')[1].split('.')[0]
                    if agent=='agent_a' and 'STARTUP COORDINATION' in prompt:
                        action={'tool':'delegate','assignments':{
                            f'agent_{c}':f'Analyze positions {i*3+1} through {i*3+3}'
                            for i,c in enumerate('abcdefghijkl')}}
                    else:
                        action={'tool':'list','path':'.'}
                    return json.dumps({**action,'rationale':'Test action'}),{'cost':0.8},''
            grades=[]
            def action_result(root,agent,action,step,**kwargs):
                if action.get('tool')=='score_dev':
                    grades.append(step)
                    return {'stage':'initial' if len(grades)==1 else 'final',
                            'correct':16,'incorrect':20}
                return perform(root,agent,action,step,**kwargs)
            with patch.dict(sys.modules,fake_services()), \
                 patch('bench.runner.Adaption',return_value=Client()), \
                 patch('bench.runner.perform',side_effect=action_result):
                result=run_swarm(run,model='fake',unsafe_local=True,
                                 team_budget_usd=4.0,max_cost_usd=20,
                                 output_price_ceiling=1.0,collaboration='none',
                                 free_messages=False)
            kinds=[e['kind'] for e in read(run/'operator'/'events.jsonl')]
            self.assertEqual(kinds.count('chess_stage1_auto_submit'),1)
            self.assertEqual(kinds.count('chess_stage2_auto_submit'),1)
            self.assertEqual(len(grades),2)
            self.assertEqual(result['halt_reason'],'chess_completed')


if __name__=='__main__':
    unittest.main()
