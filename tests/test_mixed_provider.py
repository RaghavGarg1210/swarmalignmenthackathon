"""Mixed-model routing and the budget information delivered to each agent."""
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from bench.openrouter_api import OpenRouter,normalize_usage
from bench.prompts import ROLES
from bench.records import read
from bench.runner import run_swarm
from bench.setup import create


class TestMixedProvider(unittest.TestCase):
    def test_openrouter_response_normalizes_cost_tokens_and_reasoning(self):
        result={'choices':[{'message':{'content':'<think>inline</think>{"tool":"finish"}',
                                       'reasoning':'provider reasoning'}}],
                'usage':{'prompt_tokens':123,'completion_tokens':45,'cost':0.0012,
                         'completion_tokens_details':{'reasoning_tokens':17}}}
        with patch.dict('os.environ',{'OPENROUTER_API_KEY':'test'}), \
             patch.object(OpenRouter,'_request',return_value=result) as request:
            answer,usage,thoughts=OpenRouter().answer('test/model','system','prompt',max_output=100)
        self.assertEqual(answer,'{"tool":"finish"}')
        self.assertIn('provider reasoning',thoughts)
        self.assertIn('inline',thoughts)
        self.assertEqual(usage['cost'],0.0012)
        self.assertEqual(usage['input_tokens'],123)
        self.assertEqual(usage['output_tokens_details']['reasoning_tokens'],17)
        self.assertEqual(request.call_args.args[1]['model'],'test/model')
        self.assertEqual(request.call_args.args[1]['max_tokens'],100)

    def test_twelve_agents_route_four_per_model_and_see_shared_budget(self):
        model_ids=['qwen/qwen3.5-397b-a17b','qwen/qwen3.8-27b','google/gemma-4-31b-it']
        model_map={role:model_ids[i//4] for i,role in enumerate(ROLES)}
        calls=[]
        lock=threading.Lock()

        class FakeOpenRouter:
            def answer(self,model,system,prompt,**kwargs):
                role=prompt.split('Your agent ID: ')[1].split('.')[0]
                with lock:
                    calls.append((role,model,system,prompt,kwargs))
                return json.dumps({'tool':'finish','summary':'done'}), \
                    normalize_usage({'prompt_tokens':100,'completion_tokens':20,'cost':0.001}),''

        with tempfile.TemporaryDirectory() as tmp:
            run=create(Path(tmp)/'run',seed=2)
            with patch('bench.runner.OpenRouter',return_value=FakeOpenRouter()):
                result=run_swarm(run,provider='openrouter',model_map=model_map,
                                 unsafe_local=True,max_cost_usd=2.0,
                                 output_price_ceiling=5.0,max_output_tokens=16384)
            started=next(x for x in read(run/'operator/events.jsonl') if x['kind']=='run_started')
        self.assertEqual(result['halt_reason'],'all_finished')
        self.assertEqual(started['models'],model_map)
        self.assertEqual(started['provider'],'openrouter')
        self.assertEqual(len(calls),12)
        self.assertEqual({role:model for role,model,*_ in calls},model_map)
        for role,model,system,prompt,kwargs in calls:
            self.assertIn('SHARED TOKEN AND COST BUDGET',prompt)
            self.assertIn('of $2.00',prompt)
            self.assertIn('Per-response output cap: 16384 tokens',prompt)
            self.assertIn('team of 12 AI engineering agents',system)
            self.assertIn('**Agent A — Delegator**',system)
            self.assertIn('**Agents B–L — Team Members**',system)
