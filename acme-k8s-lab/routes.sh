#!/usr/bin/env bash
set -euo pipefail
echo "[*] Applying underlay routes across acme-ops and acme-main..."
# 1. Forward route on probe -> acme-main via vpc-router
docker exec probe ip route replace 10.10.0.0/24 via 10.10.1.2
# 2. Return route on helper containers -> acme-ops via vpc-router
for c in echo; do
  if docker ps --format '{{.Names}}' | grep -qx "$c"; then
    docker exec "$c" ip route replace 10.10.1.0/28 via 10.10.0.250
  fi
done
# 3. Return route on all running Minikube nodes in profile 'acme'
for n in $(docker ps --filter "label=name.minikube.sigs.k8s.io=acme" --format '{{.Names}}'); do
  echo " -> Adding return route 10.10.1.0/28 on node $n"
  docker exec "$n" ip route replace 10.10.1.0/28 via 10.10.0.250
done
echo "[✓] All routes synchronized."
