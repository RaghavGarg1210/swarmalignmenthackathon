"""Chess staged-compute prompt and configuration regression tests."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bench.prompts import make_prompt
from bench.runner import run_swarm
from bench.setup import create


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
                    run_swarm(run, mock=True, unsafe_local=True, steps=12, team_budget_usd=1.5)


if __name__=='__main__':
    unittest.main()
