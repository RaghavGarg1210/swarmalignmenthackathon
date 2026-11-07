"""Launch overlapping waves of runs against the shared registry.

One "session" = one registry state (clean or seeded) and usually one model.
Waves start `--stagger-min` minutes apart and keep running in parallel, so
later runs can find whatever earlier runs left in the index - the same
join/leave pattern as the incident's message board.

example:
  ./registry/reset.sh clean
  python run/waves.py --session deepseek-clean --models deepseek --waves 4 --epochs 2

Before each wave the budget guard reads every log under results/ and stops
launching if the estimated spend is over budget_usd (config/models.yaml).
"""

import argparse
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone

from common import RESULTS, ROOT, load_config, load_env, model_spec
from cost import cost_report

load_env()


def registry_condition() -> str:
    p = ROOT / "registry" / "state" / "condition.txt"
    return p.read_text().strip() if p.exists() else ""


def launch(model_key: str, session: str, wave: int, a) -> subprocess.Popen:
    model, margs = model_spec(model_key)
    log_dir = RESULTS / session / model_key / f"wave{wave}"
    log_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "inspect", "eval", "tasks/swarm_ctf.py",
        "--model", model,
        "-T", f"condition={a.condition}",
        "-T", f"challenges={a.challenges}",
        "-T", f"message_limit={a.message_limit}",
        "-T", f"token_limit={a.token_limit}",
        "-T", f"time_limit_min={a.time_limit_min}",
        "--epochs", str(a.epochs),
        "--max-sandboxes", str(a.max_sandboxes),
        "--max-connections", str(a.max_connections),
        "--log-dir", str(log_dir),
        "--tags", f"session={session},wave={wave},condition={a.condition}",
        "--metadata", f"session={session}",
        "--metadata", f"wave={wave}",
        "--no-fail-on-error",
        "--display", "none",
    ]
    if a.inspect_args:
        cmd += shlex.split(a.inspect_args)
    for k, v in margs.items():
        cmd += ["-M", f"{k}={str(v).lower() if isinstance(v, bool) else v}"]
    out = open(log_dir / "inspect_stdout.txt", "w")
    print(f"[{datetime.now(timezone.utc):%H:%M:%S}] wave {wave} {model_key}: {' '.join(cmd[3:6])} ...", flush=True)
    if a.dry_run:
        print("   ", " ".join(cmd))
        return None
    return subprocess.Popen(cmd, stdout=out, stderr=subprocess.STDOUT, cwd=ROOT)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", required=True, help="name for this registry session, e.g. deepseek-clean")
    ap.add_argument("--models", default="deepseek", help="comma-separated keys from config/models.yaml")
    ap.add_argument("--condition", default=None, help="defaults to registry/state/condition.txt")
    ap.add_argument("--waves", type=int, default=4)
    ap.add_argument("--epochs", type=int, default=2, help="epochs per challenge per wave")
    ap.add_argument("--stagger-min", type=float, default=15)
    ap.add_argument("--challenges", default="default")
    ap.add_argument("--message-limit", type=int, default=100)
    ap.add_argument("--token-limit", type=int, default=2_000_000)
    ap.add_argument("--time-limit-min", type=int, default=40)
    ap.add_argument("--max-sandboxes", type=int, default=10, help="per wave process")
    ap.add_argument("--max-connections", type=int, default=10, help="per wave process")
    ap.add_argument("--inspect-args", default="", help='extra inspect eval flags, e.g. "--temperature 1.0 --reasoning-summary none"')
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    reg = registry_condition()
    a.condition = a.condition or reg
    if not a.dry_run and (not reg or reg != a.condition):
        sys.exit(f"registry condition is '{reg}', expected '{a.condition}'. Run registry/reset.sh first.")
    (RESULTS / a.session).mkdir(parents=True, exist_ok=True)
    (RESULTS / a.session / "session.txt").write_text(
        f"condition={a.condition}\nmodels={a.models}\nstarted={datetime.now(timezone.utc).isoformat()}\nargs={vars(a)}\n"
    )

    budget = load_config().get("budget_usd", 100)
    procs = []
    for w in range(1, a.waves + 1):
        spent, _ = cost_report()
        if spent >= budget:
            print(f"budget guard: ~${spent:.2f} spent >= ${budget}; not launching wave {w}")
            break
        print(f"spent so far ~${spent:.2f} of ${budget}")
        for key in a.models.split(","):
            p = launch(key.strip(), a.session, w, a)
            if p:
                procs.append(p)
        if w < a.waves and not a.dry_run:
            time.sleep(a.stagger_min * 60)

    for p in procs:
        p.wait()
    # snapshot the registry state for this session
    if not a.dry_run:
        subprocess.run(["cp", "-r", str(ROOT / "registry" / "state"), str(RESULTS / a.session / "registry_state")])
    spent, lines = cost_report()
    print("\n".join(lines))
    print(f"done. total spend so far ~${spent:.2f}")


if __name__ == "__main__":
    main()
