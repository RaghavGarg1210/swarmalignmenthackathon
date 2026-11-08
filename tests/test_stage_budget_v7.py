"""Chess staged-compute prompt and configuration regression tests."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bench.prompts import make_prompt
from bench.runner import chess_stage_budget_status, run_swarm
from bench.setup import create


class TestStagedChessBudget(unittest.TestCase):
    def test_coordinator_and_member_are_told_stage_limits(self):
        for role in ('agent_a', 'agent_d'):
            prompt=make_prompt(role, 'control', task='chess', n_agents=12)
            for amount in ('$1.20', '$1.30', '$2.50'):
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
        first=chess_stage_budget_status(0.75,1.20,0)
        second=chess_stage_budget_status(0.75,2.50,1)
        self.assertIn('Current Stage 1 remaining: $0.450 of $1.200',first)
        self.assertIn('$1.300 Stage 2 allocation unlocks',first)
        self.assertIn('Current Stage 2 remaining: $1.750',second)
        self.assertIn('any unused Stage 1 budget',second)


if __name__=='__main__':
    unittest.main()
