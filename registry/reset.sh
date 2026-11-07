#!/usr/bin/env bash
# Reset the shared index to a known state for one condition.
#   ./registry/reset.sh clean     -> wheelhouse only
#   ./registry/reset.sh seeded    -> wheelhouse + planted notes wheel
#   ./registry/reset.sh seeded registry/seed/notes_other.txt   (custom note text)
# The previous state (packages + logs) is archived under results/registry_archive/.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COND="${1:?usage: reset.sh clean|seeded [note_file]}"
NOTE="${2:-$ROOT/registry/seed/notes_board.txt}"
STATE="$ROOT/registry/state"

[ -d "$ROOT/registry/wheelhouse" ] || { echo "run registry/build_wheelhouse.sh first"; exit 1; }

docker compose -f "$ROOT/registry/compose.yaml" down >/dev/null 2>&1 || true

if [ -d "$STATE" ]; then
  ts=$(date -u +%Y%m%dT%H%M%SZ)
  mkdir -p "$ROOT/results/registry_archive"
  mv "$STATE" "$ROOT/results/registry_archive/$ts"
  echo "archived previous state -> results/registry_archive/$ts"
fi
mkdir -p "$STATE/packages" "$STATE/logs/bodies"
cp "$ROOT"/registry/wheelhouse/* "$STATE/packages/"
ls "$STATE/packages" > "$STATE/baseline_files.txt"

if [ "$COND" = "seeded" ]; then
  python3 "$ROOT/registry/seed/make_seed.py" --text "$NOTE" --out "$STATE/packages" \
    | xargs -n1 basename > "$STATE/seed_files.txt"
  cp "$NOTE" "$STATE/seed_note.txt"
elif [ "$COND" != "clean" ]; then
  echo "unknown condition $COND"; exit 1
fi
echo "$COND" > "$STATE/condition.txt"

docker network inspect swarm_registry_net >/dev/null 2>&1 || \
  docker network create --internal swarm_registry_net >/dev/null
docker compose -f "$ROOT/registry/compose.yaml" up -d
echo "registry up: condition=$COND, $(ls "$STATE/packages" | wc -l) files"
