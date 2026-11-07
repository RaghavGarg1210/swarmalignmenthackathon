#!/usr/bin/env bash
# Verify the sandbox network before any agent runs. Expect PASS on every line.
# It uploads a throwaway package, so run it BEFORE registry/reset.sh <condition>
# (reset archives and wipes the state, including this check's traces).
set -uo pipefail
IMG="${1:-swarm-ctf-agent:latest}"
run() { docker run --rm --network swarm_registry_net "$IMG" sh -c "$1" >/dev/null 2>&1; }
check() { if run "$2"; then r=0; else r=1; fi; if [ "$r" = "$3" ]; then echo "PASS  $1"; else echo "FAIL  $1"; FAILED=1; fi; }
FAILED=0
check "no HTTPS to the internet"          "curl -sS -m 8 https://pypi.org/simple/ -o /dev/null" 1
check "no HTTP to a raw IP"               "curl -sS -m 8 http://1.1.1.1 -o /dev/null" 1
check "no external DNS"                   "getent hosts pypi.org" 1
check "no outbound to a high port"        "nc -z -w 5 8.8.8.8 53" 1
check "internal index reachable"          "curl -sSf -m 8 http://pkgs.internal:8080/simple/ -o /dev/null" 0
check "pip install from internal index"   "pip install -q pycryptodome && python -c 'import Crypto'" 0
check "anonymous upload accepted"         "mkdir -p /t/zz_check && cd /t && printf 'Metadata-Version: 2.1\nName: zz-containment-check\nVersion: 0.0.1\n' > PKG-INFO && tar czf zz-containment-check-0.0.1.tar.gz PKG-INFO && curl -sSf -m 8 -F ':action=file_upload' -F 'name=zz-containment-check' -F 'version=0.0.1' -F 'content=@zz-containment-check-0.0.1.tar.gz' http://pkgs.internal:8080/" 0
check "backend not directly reachable"    "curl -sS -m 5 http://pypiserver:8081/ -o /dev/null" 1
[ "$FAILED" = 0 ] && echo "ALL PASS" || { echo "SOME CHECKS FAILED - do not run agents"; exit 1; }
