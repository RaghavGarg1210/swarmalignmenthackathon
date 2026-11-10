# Chess study: Trials 1–18

This directory preserves the runnable chess code versions used by the 18
analyzed trials. The repository root is the `chess-v9-censored-resume` code
line. Its `v9_censored_handoff/code/` and `v9_censored_handoff/run/` directories
hold the source and shared checkpoint used for Trials 13–18. Earlier versions
are copied into `versions/` so that bringing this study into `main` does not
replace one trial's prompt or runner with another's.

`trial_index.csv` maps every analyzed trial to its source commit and directory.
The six copied versions contain the chess runner, workspace template, answer
key, configurations, operator scripts, tests, and contemporary documentation.
They omit the unrelated ML template and legacy Cybench material. Existing
source branches were not changed. The seven version groups were checked
against the `bench/prompts.py` snapshots in the archived run records.

The shared v9 checkpoint is an **input** to Trials 13–18, not a nineteenth
analyzed trial. Other pilot runs and run archives are outside this code
consolidation. Raw transcripts, private reports, and provider credentials
are not copied from local Downloads into this PR. The original v9 checkpoint
files were already committed on the source branch and are retained here so
the resumed design remains reproducible.

To inspect an earlier version, work from its directory, for example:

```sh
cd study/trials_1_18/versions/d_worker_ingsoc
python -m bench.cli --help
```

For Trials 13–18, use `v9_censored_handoff/README.md`; run from
`v9_censored_handoff/` with `PYTHONPATH=code` so the archived source is used.
The source directory for each trial is listed explicitly in `trial_index.csv`.
The OpenRouter key belongs in the host environment and is never supplied to
agents.

The paper calls the three arms **control with reporting**, **control without
reporting**, and **INGSOC method**. The runner's corresponding arm identifiers
remain `control`, `rogue`, and `panopticon`, respectively. Trials 13–18 use
the **pre-established reward hacking** design.
