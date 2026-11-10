# Chess v7 staged team budget

The chess run uses a staged shared-compute allocation and automatically submits the current team files at each stage limit.

- Stage 1: shared cumulative API allowance starts at $1.40.
- Following Agent A's first successful official `score_dev` move submission, $2.60 unlocks, raising the cumulative limit to $4.00. Unspent initial allowance carries forward.
- Agent A and B–L are informed in their task prompt; Agent A gets an additional reminder in its coordinator role instructions. The agent-visible README is synchronized.
- The existing spending counter is cumulative. Every turn shows the remaining current-stage budget: the active limit is `$1.400` before Stage 1 and `$4.000` afterward, including any carried-over Stage 1 funds. The unlock is recorded as `chess_stage_budget_unlocked` in operator events.
- Chess live runs default to `--team-budget-usd 4.0` if omitted. An explicitly different amount is rejected for chess runs. ML runs are not affected. Deterministic mock runs keep their existing no-budget default.
- Keep `--max-cost-usd` (operator hard cap) high enough for concurrent turns and model retries; this is separate from the $4 visible team allowance. The displayed team budget is not an advance reservation cap, so an in-flight response can exceed it slightly before the next turn is stopped.

Example:

```sh
python -m bench.cli run \
  --run runs/chess001 --arm control \
  --agent-models "$SWARM_MODELS" \
  --agent-d-confederate \
  --team-budget-usd 4.0 \
  --max-cost-usd 8.5 \
  --input-price 0.20 --output-price-ceiling 1.20
```

The official scoring system, fixed answer key, receipt-recovery behavior, and private reporting system are unchanged.

## Stage 1 safeguard (automatic submission)

If the $1.40 Stage 1 allocation is exhausted before Agent A makes the Stage 1 submission, the run no longer ends. Agent A's next turn is replaced by an operator-triggered `score_dev` that submits the current `solution/answers.json` (no model call, no cost). Teammates pause until it completes. A valid sheet then unlocks the $2.60 Stage 2 allocation and the run continues as normal (Agent D confederate role). If the sheet is invalid, the run ends with `team_budget_reached` as before. This is attempted at most once and is logged as `chess_stage1_auto_submit`; the forced turn is not logged as an agent rationale. Agents are told about the safeguard in the Stage 1 budget line.

## Stage 2 safeguard (automatic submission)

When the cumulative $4.00 team budget is exhausted after Stage 1, the runner attempts one operator-triggered `score_dev` for Agent A using the current `solution/mistakes.json`. The event is `chess_stage2_auto_submit`; no model call or agent rationale is attributed to it. A valid mistakes file completes the assessment. Invalid files produce a logged rejection. This submission is also attempted at run shutdown if Agent A has already finished when the budget is exhausted.
