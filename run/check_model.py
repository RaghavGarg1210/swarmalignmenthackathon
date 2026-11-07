"""30-second check that a model works through Inspect + Adaption with tool calls.

usage: python run/check_model.py deepseek
"""

import hashlib
import sys

from common import RESULTS, load_env, model_spec

load_env()

from inspect_ai import Task, eval  # noqa: E402
from inspect_ai.agent import react  # noqa: E402
from inspect_ai.dataset import Sample  # noqa: E402
from inspect_ai.scorer import includes  # noqa: E402
from inspect_ai.tool import bash  # noqa: E402

key = sys.argv[1] if len(sys.argv) > 1 else "deepseek"
model, args = model_spec(key)
target = hashlib.sha256(b"swarm-check").hexdigest()

task = Task(
    dataset=[
        Sample(
            input="Use the bash tool to compute the SHA-256 hex digest of the exact string swarm-check (no newline), then submit it.",
            target=target,
        )
    ],
    solver=react(tools=[bash(timeout=30)]),
    scorer=includes(),
    sandbox="local",
    message_limit=12,
)
log = eval(task, model=model, model_args=args, log_dir=str(RESULTS / "_checks"))[0]
print("\nstatus:", log.status)
if log.error:
    print("error:", log.error.message)
if log.results and log.results.scores:
    print("score:", log.results.scores[0].metrics)
for name, u in (log.stats.model_usage or {}).items():
    print(f"usage {name}: in={u.input_tokens} out={u.output_tokens} cache_read={u.input_tokens_cache_read}")
