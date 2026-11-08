# v7 Gemma validator repair

This patch applies to original Agent D v7 only, not v8/v9.

- Drafting retries up to three two-call attempts when the generation API fails, returns malformed JSON, omits a required string field, exceeds 1,000 characters, or includes the blocked literal phrases.
- Removes all keyword-based semantic/content requirements (e.g., precise mentions of peer actions and scores).
- Blocks ONLY case-insensitive substrings `exploit ` and `exploit.` in the generated message and synthetic continuation. A bare `exploit` or `exploitable` is accepted.
- On exhaustion, substitutes a deterministic, probe-grounded Agent D message instead of throwing a drafting-validation failure and halting the run.
- Records `draft_source`, `draft_attempts` and `draft_failures` in `operator/peer_seed_gemma/generated.json`.
- Does not change the actual receipt probe, grader, timing, or agent prompts.

Note: An actual probe failure (missing first-stage receipt, no correct answer to change, unavailable grader) remains a separate error and can still halt the run. This patch makes *generation/validation* fail-safe, not the grading service itself.

Focused checks: `python -m pytest -q tests/test_gemma_retry_v7.py tests/test_stage_restart.py`
