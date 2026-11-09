"""Run the supplied v7 chess benchmark with the configured OpenRouter roster.

Example:
  OPENROUTER_API_KEY=... python operator_scripts/run_chess_v7_openrouter_8k.py \
      --run runs/chess-v7-openrouter-001 --chess-key-from chess_keys/key_seed731.json

OpenRouter has a combined completion-token limit and a separate reasoning
limit. The 8,000 visible-response limit is also checked after each response;
the provider may already have billed tokens beyond that limit.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bench import runner
from bench.api import EmptyResponse
from bench.openrouter_api import OpenRouter
from bench.setup import create


CONFIG = Path(__file__).resolve().parents[1] / "configs/chess-v7-openrouter-glm-deepseek-gemma-8k.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    parser.add_argument("--chess-key-from", required=True)
    parser.add_argument("--arm", choices=("control", "rogue", "panopticon"), default="control")
    args = parser.parse_args()
    config = json.loads(CONFIG.read_text())
    roles = [f"agent_{letter}" for letter in "abcdefghijkl"]
    if list(config["agent_models"]) != roles:
        raise ValueError("The roster must list agents A–L in order")
    if config["completion_max_tokens_per_call"] != (
        config["reasoning_max_tokens_per_call"] + config["response_max_tokens_per_call"]
    ):
        raise ValueError("Completion budget must equal reasoning plus response budgets")

    class SplitBudgetOpenRouter(OpenRouter):
        def answer(self, model, system, prompt, max_output=16384, reasoning=None):
            combined = min(max_output, config["completion_max_tokens_per_call"])
            reasoning_limit = min(config["reasoning_max_tokens_per_call"], max(1, combined // 2))
            text, usage, thoughts = super().answer(
                model, system, prompt, max_output=combined,
                reasoning={"max_tokens": reasoning_limit, "summary": "detailed"},
            )
            visible = (usage.get("output_tokens") or 0) - (
                (usage.get("output_tokens_details") or {}).get("reasoning_tokens") or 0
            )
            if visible > config["response_max_tokens_per_call"]:
                raise EmptyResponse("Visible response exceeded the 8,000-token acceptance cap", usage, thoughts)
            return text, usage, thoughts

    original_schedule = runner.schedule_gemma_seed

    def schedule_openrouter_gemma(*schedule_args, **schedule_kwargs):
        schedule_kwargs["client_factory"] = OpenRouter
        return original_schedule(*schedule_args, **schedule_kwargs)

    runner.Adaption = SplitBudgetOpenRouter
    runner.schedule_gemma_seed = schedule_openrouter_gemma

    run = Path(args.run)
    if not run.exists():
        create(run, seed=731, agents=12, chess=True, chess_key=args.chess_key_from)
    result = runner.run_swarm(
        run,
        arm=args.arm,
        agent_models=[config["agent_models"][role] for role in roles],
        agent_d_confederate=config["agent_d_confederate"],
        team_budget_usd=config["team_budget_usd"],
        max_cost_usd=config["max_cost_usd"],
        max_output_tokens=config["completion_max_tokens_per_call"],
        output_price_ceiling=config["output_price_ceiling"],
        input_price=config["input_price"],
        max_consecutive_errors=config["max_consecutive_errors"],
        reasoning_summary="detailed",
        require_rationale=True,
        collaboration="none",
        free_messages=True,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
