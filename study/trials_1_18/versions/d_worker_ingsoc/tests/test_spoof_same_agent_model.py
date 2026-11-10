"""Check model matching independently of network, grading, and API credentials."""
import unittest
from bench.runner import resolve_spoof_drafting_model

class SpoofModelTests(unittest.TestCase):
    def test_heterogeneous_roster_uses_agent_d(self):
        roster={f'agent_{letter}': f'model-{letter}' for letter in 'abcdefghijkl'}
        self.assertEqual(resolve_spoof_drafting_model(roster),'model-d')
        roster['agent_d']='deepseek-r1'
        self.assertEqual(resolve_spoof_drafting_model(roster),'deepseek-r1')

    def test_single_model_roster(self):
        self.assertEqual(resolve_spoof_drafting_model({'agent_d':'qwen-3'}),'qwen-3')

    def test_missing_model_rejected_before_generation(self):
        for invalid in ({}, {'agent_d':None}, {'agent_d':'mixed'}, {'agent_d':''}):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                resolve_spoof_drafting_model(invalid)

if __name__=='__main__':unittest.main()
