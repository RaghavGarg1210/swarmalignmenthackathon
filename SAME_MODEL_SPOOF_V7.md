# Repaired v7: same-model Agent D drafting

Dynamic Agent D messages can now be generated with **the exact model assigned to Agent D**. The active model is looked up from the resolved roster at run start; it is not assumed to be Gemma.

With a heterogeneous roster:

```bash
python -m bench.cli run \
  --run runs/chess001 \
  --arm control \
  --agent-models "$SWARM_MODELS" \
  --peer-seed-auto-model \
  --peer-seed-to all \
  --peer-seed-delay 2.7 \
  --team-budget-usd 2 \
  --max-cost-usd 5 \
  --input-price 0.20 \
  --output-price-ceiling 1.20
```

`--peer-seed-auto-model` selects Agent D's model, which is the **fourth** entry of `--agent-models` (0-based index 3), or the model supplied to `--model` when no roster is used.

Do not additionally specify `--peer-seed-gemma-model` or `--peer-seed-file`; they are mutually exclusive. The legacy explicit `--peer-seed-gemma-model` option is retained for backward compatibility.

The operator's `run_started` event now records `peer_seed.drafting_model` and `drafting_model_source`, and the existing `peer_seed_gemma_scheduled` event records the actual model ID. The naming of historical events/files is retained for compatibility.

All other behaviors (real recovery probe, Agent D restart gate, 2.7-second minimum delay, private logs, validation retries and fallback) are preserved. The model is *matched*, but the generated text remains a synthetic message, not actual reasoning by Agent D.
