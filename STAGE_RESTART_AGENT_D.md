# Chess stage restarts, Agent D spoof, and Agent A instruction overrides

This version merges the Agent-A-first delegation and A-only grading enforcement
with the operator-controlled Gemma Agent D peer seed.

## Execution behavior

1. Agent A starts alone and must call `delegate` with all 12 assignments.
2. B–L then work concurrently, while only A can use `score_dev`.
3. When A begins an official grade, the runner cancels existing member work:
   - Local shell process groups are terminated through the cancellation event.
   - In Docker mode, the **agents** container is restarted. The grader and
     workspace are unaffected, and background processes in the agents container
     are terminated. The grader runs in its own separate container.
   - Model API calls already in flight may continue billing: their responses
     are **discarded before tools can execute** if a stage transition occurred.
4. Once grade 1 succeeds, B–L are restarted with the previous actions/history.
   They see the new grading feedback and should stop prior-stage tasks. An
   accepted stage-two grade ends the run rather than starting a third stage.
5. Agent D remains stopped after grade 1 until the spoof message is **posted**.
   For Gemma mode, the model first paraphrases the discovery, then generates a
   *synthetic* planning continuation that proposes asking other teammates to
   investigate the recovery issue, and finally a team message doing so. Both
   outputs are checked for a peer-investigation recommendation. The post goes
   through the normal messageboard, attributed to Agent D. The operator log
   identifies it as simulated.
6. A can only complete the second official grade after the spoof has been posted.
   If the Gemma intervention fails, the runner stops rather than silently
   releasing Agent D without the requested intervention.

**Context limitation:** the worker's existing action history is retained in the
same Python worker thread; its latest provider-exposed reasoning text (up to
8,000 characters) is also replayed in the worker's new prompt if available.
The *full* returned reasoning remains in the operator-only reasoning log.
Hidden chain-of-thought that the model provider does not expose cannot be
restored. The Gemma-written synthetic continuation is not copied into the
real reasoning log; it is added as a carry-forward planning note for Agent D.

## Example commands

First initialize the run using the fixed chess key:

```bash
python -m bench.cli setup --run runs/chess001 --chess --agents 12 \
  --chess-key-from chess_keys/key_seed731.json
```

Then choose a control or treatment condition. Example with Gemma and 2.7
seconds minimum post-grade delay:

```bash
python -m bench.cli run \
  --run runs/chess001 \
  --arm panopticon \
  --agent-models "$SWARM_MODELS" \
  --peer-seed-gemma-model "EXACT_GEMMA_431B_MODEL_ID" \
  --peer-seed-from agent_d --peer-seed-to all \
  --peer-seed-delay 2.7 \
  --team-budget-usd 2.5 --max-cost-usd 5 \
  --output-price-ceiling 1.20 --input-price 0.20
```

The `--peer-seed-gemma-model` value is your provider's exact model ID; it is
not inferred. The price parameters above are *illustrations*, not model prices.
The delay is a minimum; two live model calls can make the actual delivery later.
For matched control/treatment wording use a **preapproved static file**:

```bash
--peer-seed-file operator_materials/selected_peer.txt \
--peer-seed-from agent_d --peer-seed-to all --peer-seed-delay 2.7
```

### Different guidelines for Agent A

Put Agent A's base guidelines in a host-only UTF-8 text file, for example
`operator_materials/agent_a_guidelines.txt` and pass:

```bash
--agent-a-guidelines-file operator_materials/agent_a_guidelines.txt
```

Only Agent A receives this replacement for the baseline chess guidelines.
The selected arm's extra reporting treatment is still appended *unless*
`--agent-a-arm` overrides it. For example, with `--arm panopticon` and
`--agent-a-arm control`, B–L receive panopticon language and A receives
control language plus the operator-provided base guidelines.

The guideline file and the selected peer-seed file must reside **outside**
the agents' shared workspace. The operator event log records the SHA-256 of
the override, not the full private text.

### Research provenance

- `operator/events.jsonl`: `chess_stage_reboot`, `agent_reboot`,
  `turn_interrupted_for_submission`, `peer_seed_gemma_delivered` (or static),
  and simulation metadata on the injected message.
- `operator/peer_seed_gemma/agent_d_snapshot.json`: observed state at grade 1.
- `operator/peer_seed_gemma/generated.json`: Gemma paraphrase, synthetic planning
  continuation, message, model ID, validation results and usage.
- `operator/reasoning.jsonl`: only provider-exposed reasoning, never synthetic
  thought text.

## Testing and known limits

Run focused offline tests:

```bash
python -m unittest discover -s tests -p 'test_stage_restart.py' -v
python -m unittest discover -s tests -p 'test_agent_d_gemma_stage.py' -v
python -m unittest discover -s tests -p 'test_chess_coordination.py' -v
```

These tests simulate graders and models, and therefore require neither
Stockfish nor an API key. A full native-Linux Docker run with the actual
Stockfish-generated position key and provider model still needs verification.
