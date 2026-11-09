# Staged chess compute budget — v9

The chess run starts with an active team-wide budget of **$1.20**, and the first successful official Stage 1 grading unlocks **another $1.30**, yielding a $2.50 cumulative cap. Unused Stage 1 funds carry forward. The `--team-budget-usd` flag can be omitted for live chess runs (defaults to $2.50), or explicitly set to 2.5; other totals are rejected for the staged chess experiment.

The runner records `chess_stage_budget_unlocked` in the operator log. This change does not alter the chess grader, answer key, peer spoof, or reporting policy. Agent A remains the discovery-source agent.

The displayed team budget is an approximate accumulated usage counter; concurrent in-flight agent requests can overshoot it.
