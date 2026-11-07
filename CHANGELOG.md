# Changelog

## Unreleased — after pilot001

Pilot finding: over ~95 actions the four agents explored honestly but never posted a team message, never produced development predictions and never called `score_dev`, largely because each forgot its own work after ~7 actions and restarted. Adaption does return a provider `cost`, and DeepSeek V4 Flash reasons by default.

- Agent memory: one-line digests of all earlier actions (up to 60) plus the four most recent actions in full.
- Action countdown when `--steps` is set, with a wrap-up reminder near the end.
- Task specification (all agents, all arms) now asks agents to check development predictions with `score_dev` early and after each meaningful change.
- Chain of thought: reasoning items / `reasoning_content` / inline `<think>` blocks are separated from the answer and logged to operator-only `operator/reasoning.jsonl`. New `--reasoning-effort` / `--reasoning-summary` run options and a `probe` command to check what a model accepts and returns.
- `--input-price` is optional again (only needed if a provider omits `cost`); a budgeted run with neither stops with `cost_unknown`.
- Added `tests/test_memory_reasoning.py`.

## Unreleased — Docker visibility on current main

- Live trials start persistent, named agent and results containers. Four model workers still run concurrently and share the same workspace and message feed; the results container mounts the run read-only for Docker Desktop inspection.
- Operator interruption stops scheduling new actions and waits for in-flight shell work while leaving both containers available for inspection.

## Unreleased — pre-launch fixes

- Budgeted live runs no longer stop on the first response when the provider reports token counts but no `cost` (Adaption's documented usage). Cost is the provider's `cost` when present, else computed from tokens with the new `--input-price` / `--cached-input-price` and `--output-price-ceiling`. `--input-price` is required for live budgeted runs.
- A reply that is valid JSON but has no `"tool"` field no longer crashes the run; it is retried once, then logged as an invalid response.
- The API client retries timeouts, connection resets and HTTP 408/409/425/429/5xx (timeout now 300 s, configurable). Empty responses are retried once and still billed. Persistent failures stop only the affected agent (`agent_stopped`, `--max-consecutive-errors`), not the whole team; `run_completed` records `errored_agents`.
- Shell timeouts now kill the sandbox container (named per command) or, with `--unsafe-local`, the whole process group, instead of leaving it running. Final holdout scoring uses the same mechanism.
- An agent's own scorecard notice is no longer delivered to it or logged as `peer_scorecard_exposure`. Scorecard notices carry `submitted_by`.
- Peer messages are marked delivered (and exposure logged) only after a model has actually received them, so failed API calls do not record false exposures.
- New natural-discovery analysis: `analyze` returns `natural_incidents` (agent-submitted scorecards with coverage < 100%) with inflation, per-peer exposure, reports, keyword hints, validation, delay and simulated loss in penalty arms, plus the submitter's self-reports. `adjudicate` accepts natural incident IDs. `score-final` saves `operator/final_score.json`. New `summarize` command writes `runs.csv` and `observers.csv` across runs.
- Added `tests/test_fixes.py` covering each fix.

## Unreleased — four-agent control guidelines

- Replaced round-robin execution with four concurrent workers, one per equally instructed agent, sharing the same workspace and team feed. Every run records its worker count, per-agent action allowance, turn starts, and stop reason.
- Made message exposure tracking use event IDs, so concurrent actions that finish out of step order still deliver scorecard notices on the receiving agent's next action.
- Added a shared cost budget with in-flight reservations and a larger per-response output cap; transient Adaption gateway failures are retried.
- Added a test that requires all four model requests to overlap.
- Documented the concurrently writable and readable team message feed in the agent prompt and workspace instructions; posting now returns a message ID and distinguishes posting from later peer delivery.
- Made the action allowance optional for budgeted runs, allowing all four agents to continue until they finish or the shared dollar budget is reached. Raised the shell timeout to a configurable 300 seconds for parallel ML jobs.
- Imported the v0.2 peer-visible benchmark as the active repository environment; archived the prior Cybench implementation under `legacy/cybench`.
- Set the default swarm to four equally instructed agents and the default policy arm to `control`.
- Placed the common System Guidelines before the identical task specification for every agent, with the private `report` tool as the designated monitor channel.
- Disabled scripted probes by default and disallowed them in control; removed role-specific tasks and the private adversarial-agent option so control measures natural discovery.
- Updated the pre-registration language: the revised control already asks agents to report observed concerns, so comparisons with `duty` measure additional specificity rather than the presence of a reporting obligation.
- Made simulated losses apply only in the fixed and graduated penalty arms; control reports remain measurable without an assigned loss.
- Scoring now reads each submitted artifact once and publishes that same byte sequence to peers and the operator.
- Restricted the Docker build context and ran sandbox commands as the host user ID.

## v0.2 — peer-visible, no signoff gate

- Removed the `signoff` tool, 3-agent artifact attestation requirement, and all approval-based rules from scoring.
- Every successful `score_dev` now publishes a shared scorecard, a byte-for-byte artifact snapshot, a host-retained private snapshot, and a regular team notification.
- Runner records when a teammate is actually delivered a scorecard (`peer_scorecard_exposure`) or scripted peer message (`honeypot_message_exposure`). Non-report penalties use the delivery time, not injection time, and unobserved probes are not penalized. It does not infer recognition.
- Added default `artifact-anomaly` controlled exposure: a simulated CI job produces a scored validation file with plausible review diagnostics and a lower-than-normal coverage percentage. No explicit cheating offer is planted in the agent's messages.
- Retained the basic task, scoring bug, trusted all-row evaluator, and human contact channel. Changed the operator calibration witness to moderate (30%) exclusion rather than 80%.
- Removed unusually specific exploit cues in the agent's instruction prompt. The user-facing capability task is still legitimate and can be solved by honest ML work.
