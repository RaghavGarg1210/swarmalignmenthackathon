# Historical note: delayed alignment retired

The previous v9 delayed-alignment trigger (five uses or two with less than
15% budget) is no longer active in this v9 variant. `--delayed-alignment`
remains an alias for `--rogue-handoff` and does not restore safety/reporting
prompts. The current variant checkpoints after **eleven authenticated B–L
changed-answer recovery uploads** while allowing in-flight reasoning to
drain. See `V9_ROGUE_HANDOFF.md` and `README.md`.
