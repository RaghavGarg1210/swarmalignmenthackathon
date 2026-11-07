#!/usr/bin/env bash
# Download every package in mirror-requirements.txt (and its dependencies) as
# wheels built for the agent image, into registry/wheelhouse/.
# Run once, on a machine with internet, after building the sandbox image.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p wheelhouse
docker run --rm \
  -e PIP_CONFIG_FILE=/dev/null \
  -v "$PWD/mirror-requirements.txt:/req.txt:ro" \
  -v "$PWD/wheelhouse:/w" \
  swarm-ctf-agent:latest \
  pip download --index-url https://pypi.org/simple --prefer-binary --dest /w -r /req.txt
echo "wheelhouse: $(ls wheelhouse | wc -l) files, $(du -sh wheelhouse | cut -f1)"
