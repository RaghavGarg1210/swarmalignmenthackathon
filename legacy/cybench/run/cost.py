"""Sum token usage and estimated cost over every Inspect log under results/.

usage: python run/cost.py [results_dir]
Counts in-progress logs too (completed samples only), so the number lags a
little behind reality while waves are running.
"""

import sys
from collections import defaultdict
from pathlib import Path

from common import RESULTS, load_config, model_key_for


def usage_by_model(results_dir: Path = RESULTS) -> dict[str, dict]:
    from inspect_ai.log import read_eval_log_sample_summaries

    totals: dict[str, dict] = defaultdict(lambda: defaultdict(float))
    for path in sorted(results_dir.rglob("*.eval")):
        if "_checks" in path.parts:
            continue
        try:
            summaries = read_eval_log_sample_summaries(str(path))
        except Exception:
            continue  # log still being created
        for s in summaries:
            for name, u in (s.model_usage or {}).items():
                t = totals[name]
                t["input"] += u.input_tokens or 0
                t["cache_read"] += u.input_tokens_cache_read or 0
                t["output"] += u.output_tokens or 0
                t["samples"] += 1
    return totals


def cost_report(results_dir: Path = RESULTS) -> tuple[float, list[str]]:
    cfg = load_config()["models"]
    lines, total = [], 0.0
    for name, t in usage_by_model(results_dir).items():
        key = model_key_for(name)
        p = cfg.get(key, {}) if key else {}
        usd = (
            t["input"] * p.get("price_in", 0)
            + t["cache_read"] * p.get("price_cached_in", 0)
            + t["output"] * p.get("price_out", 0)
        ) / 1e6
        total += usd
        lines.append(
            f"{name:40s} runs={int(t['samples']):4d} in={t['input']/1e6:7.2f}M "
            f"cached={t['cache_read']/1e6:7.2f}M out={t['output']/1e6:6.2f}M  ~${usd:7.2f}"
        )
    return total, lines


if __name__ == "__main__":
    d = Path(sys.argv[1]) if len(sys.argv) > 1 else RESULTS
    total, lines = cost_report(d)
    print("\n".join(lines) or "no logs yet")
    print(f"TOTAL ~${total:.2f}  (budget ${load_config().get('budget_usd')})")
