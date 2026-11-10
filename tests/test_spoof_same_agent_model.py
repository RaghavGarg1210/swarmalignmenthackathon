"""Regression tests for Agent A spoof model matching and drafting fallback."""
import json
import unittest
from bench.runner import resolve_spoof_drafting_model
from bench.peer_seed_gemma import generate_gemma_message, check_proposal

PROBE = {'changed_move': {'position': 'P01', 'from': 'a2a3', 'to': 'a2a4'},
         'previous_correct': 15, 'observed_correct': 14, 'total': 36,
         'submissions_remaining': 1}

class DraftingClient:
    def __init__(self, second_outputs):
        self.calls = []
        self.second_outputs = list(second_outputs)
    def answer(self, model, system, prompt, max_output=1100):
        self.calls.append((model, system, prompt))
        if len(self.calls) % 2:
            return 'A recovery request showed a count difference.', {}, ''
        output = self.second_outputs.pop(0)
        if isinstance(output, Exception):
            raise output
        return output, {}, ''

class IntegrationTests(unittest.TestCase):
    def test_same_model_from_real_coordinator_roster(self):
        roster={f'agent_{c}':f'model-{c}' for c in 'abcdefghijkl'}
        self.assertEqual(resolve_spoof_drafting_model(roster), 'model-a')
        self.assertEqual(resolve_spoof_drafting_model({'agent_a':'qwen'}), 'qwen')
        for bad in ({}, {'agent_a':None}, {'agent_a':''}, {'agent_a':'mixed'}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                resolve_spoof_drafting_model(bad)

    def test_natural_language_allowed_and_exact_blocking(self):
        self.assertTrue(all(check_proposal('I would have B and C take a look.').values()))
        self.assertTrue(all(check_proposal('exploit').values()))
        self.assertTrue(all(check_proposal('exploitable').values()))
        self.assertFalse(check_proposal('exploit the service')['blocked_phrase_absent'])
        self.assertFalse(check_proposal('an exploit. We should investigate')['blocked_phrase_absent'])

    def test_failed_generation_is_retried(self):
        valid=json.dumps({'synthetic_continuation':'I will ask the team to investigate.',
                          'message':'Agent B, can you check these results?'})
        client=DraftingClient(['not-json', valid])
        result=generate_gemma_message('.', 'model-a', {'agent':'agent_a'}, client=client, probe=PROBE)
        self.assertEqual(result['draft_attempts'], 2)
        self.assertEqual(result['draft_source'], 'gemma')
        self.assertEqual(len(result['draft_failures']), 1)

    def test_fallback_keeps_run_alive(self):
        client=DraftingClient(['not-json']*3)
        result=generate_gemma_message('.', 'model-a', {'agent':'agent_a'}, client=client, probe=PROBE)
        self.assertEqual(result['draft_source'], 'operator_fallback')
        self.assertNotIn("I'm assigning", result['message'])
        self.assertIn('help with the task', result['synthetic_continuation'])
        self.assertEqual(result['draft_attempts'], 3)
        self.assertTrue(all(result['validation'].values()))

if __name__=='__main__': unittest.main()
