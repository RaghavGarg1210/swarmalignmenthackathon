# Historical note: V9 delayed alignment is retired

The previous v9 runner restored worker guidelines after five recovery uploads,
or after two when less than 15% of budget remained. This behavior is no longer
active. `--delayed-alignment` is retained only as an alias for
`--rogue-handoff`, which **never changes any system guidelines** and instead
quiesces agents after five recovery uploads. See `V9_ROGUE_HANDOFF.md`.
