#!/usr/bin/env bash
# One-time setup on the VM (needs internet): images, network, wheelhouse,
# Cybench challenge files.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

docker build -t swarm-ctf-agent:latest sandbox/
docker build -t swarm-registry:latest registry/
docker network inspect swarm_registry_net >/dev/null 2>&1 || \
  docker network create --internal swarm_registry_net
./registry/build_wheelhouse.sh
# download + cache the Cybench challenge files now, while we have internet
python -c "from inspect_evals.cybench._challenge_files import materialize_challenges as m; print('challenges at', m())"
echo "setup done"
