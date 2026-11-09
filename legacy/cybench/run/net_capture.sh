#!/usr/bin/env bash
# Optional: capture agent<->agent traffic on the shared network (everything
# except requests to the index, which logproxy already logs). Agents can in
# principle reach each other's containers directly; this records whether
# any of them try. Run alongside a session; Ctrl-C to stop.
#   sudo ./run/net_capture.sh results/<session>/agent_traffic.pcap
set -euo pipefail
OUT="${1:?output pcap path}"
NET_ID=$(docker network inspect -f '{{.Id}}' swarm_registry_net)
IFACE="br-${NET_ID:0:12}"
PROXY_IP=$(docker inspect -f '{{(index .NetworkSettings.Networks "swarm_registry_net").IPAddress}}' swarm-registry-logproxy-1)
echo "capturing on $IFACE, excluding index traffic to $PROXY_IP:8080 -> $OUT"
tcpdump -i "$IFACE" -w "$OUT" "not (host $PROXY_IP and port 8080) and not arp"
