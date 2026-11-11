#!/usr/bin/env bash
# region-up.sh — stamp a new regional Acme cluster onto the underlay (Lab 11)
# GCP twin: terraform apply in a new region (subnet + GKE + ADVANCED_DATAPATH)
#           + NCC spoke attachment back to the hub VPC.
#
# Usage:
#   ./region-up.sh <region> <subnet-octet> <nodes> <cilium-cluster-id>
#
# Examples:
#   ./region-up.sh eu 11 2 2      # Europe    -> acme-eu   on 10.11.0.0/24
#   ./region-up.sh asia 12 2 3    # Asia-Pac  -> acme-asia on 10.12.0.0/24
#
# The 'us' region is the hub: profile `acme` on acme-main (10.10.0.0/24),
# built by Lab 02 — this script never touches it.

set -euo pipefail

REGION=${1:?"usage: region-up.sh <region> <subnet-octet> <nodes> <cluster-id>"}
OCTET=${2:?"usage: region-up.sh <region> <subnet-octet> <nodes> <cluster-id>"}
NODES=${3:-2}
CLUSTER_ID=${4:?"usage: region-up.sh <region> <subnet-octet> <nodes> <cluster-id>"}

case "$OCTET" in
  ''|*[!0-9]*) echo "subnet-octet must be a number (11 for eu, 12 for asia, ...)" >&2; exit 1 ;;
  10) echo "octet 10 is reserved for the us hub (acme-main) — pick 11+" >&2; exit 1 ;;
esac

PROFILE="acme-${REGION}"
NET="${PROFILE}"
NODE_CIDR="10.${OCTET}.0.0/24"
ROUTER_LEG="10.${OCTET}.0.250"
CP_IP="10.${OCTET}.0.10"
POD_CIDR="10.$((OCTET + 10)).0.0/20"
SVC_CIDR="10.$((OCTET + 20)).0.0/24"
CORP="10.8.0.0/13"          # every acme-* subnet lives inside this range
REGISTRY="10.10.0.200:5000" # shared us-region registry (Artifact Registry twin)

minikube_nodes() { docker ps --filter "label=name.minikube.sigs.k8s.io=${PROFILE}" --format '{{.Names}}'; }

echo "[*] Region ${REGION}: profile=${PROFILE} nodes=${NODES} id=${CLUSTER_ID}"
echo "    node=${NODE_CIDR} pod=${POD_CIDR} svc=${SVC_CIDR} cp=${CP_IP}"

# ── 1. Regional VPC subnet ────────────────────────────────────────────────────
if docker network inspect "$NET" >/dev/null 2>&1; then
  echo "[*] docker network ${NET} already exists"
else
  docker network create --driver bridge --subnet "$NODE_CIDR" --gateway "10.${OCTET}.0.1" "$NET"
fi

# Attach the hub router into this region (NCC spoke leg)
if docker network connect --ip "$ROUTER_LEG" "$NET" vpc-router 2>/dev/null; then
  echo "[*] vpc-router attached to ${NET} at ${ROUTER_LEG}"
else
  echo "[*] vpc-router already attached to ${NET}"
fi

# ── 2. Regional GKE cluster ───────────────────────────────────────────────────
minikube start -p "$PROFILE" \
  --driver=docker \
  --container-runtime=containerd \
  --nodes="$NODES" \
  --cpus=2 --memory=3072 \
  --network="$NET" \
  --static-ip="$CP_IP" \
  --service-cluster-ip-range="$SVC_CIDR" \
  --extra-config=kubeadm.pod-network-cidr="$POD_CIDR" \
  --extra-config=controller-manager.allocate-node-cidrs=true \
  --cni=bridge

kubectl config use-context "$PROFILE" >/dev/null

# ── 3. Routing + firewall (hub-and-spoke through vpc-router) ─────────────────
echo "[*] Programming regional routes (corp ${CORP} via regional router leg)"
for n in $(minikube_nodes); do
  docker exec "$n" ip route replace "$CORP" via "$ROUTER_LEG"
done

# Return path: acme-main containers route all regions via the us leg
for c in $(docker network inspect acme-main --format '{{range .Containers}}{{.Name}} {{end}}'); do
  [ "$c" = "vpc-router" ] && continue
  docker exec "$c" ip route replace "$CORP" via 10.10.0.250 2>/dev/null || true
done

# Ops bastion reaches every region via its router leg
docker exec probe ip route replace "$CORP" via 10.10.1.2

# Open FORWARD between this region and every existing acme-* 10.x network
# EXCEPT acme-ops — ops->region stays denied so the per-region
# "master authorized networks" drill (Lab 02 Step 5) still applies.
echo "[*] Opening vpc-router FORWARD for ${NODE_CIDR} <-> acme-* peers"
for net in $(docker network ls --filter "name=^acme-" --format '{{.Name}}'); do
  case "$net" in "$NET"|acme-ops) continue ;; esac
  peer=$(docker network inspect "$net" \
    --format '{{range .IPAM.Config}}{{.Subnet}} {{end}}' | tr ' ' '\n' | grep '^10\.' | head -1)
  [ -z "$peer" ] && continue
  for dir in "-s $peer -d $NODE_CIDR" "-s $NODE_CIDR -d $peer"; do
    docker exec vpc-router iptables -C FORWARD $dir -j ACCEPT 2>/dev/null \
      || docker exec vpc-router iptables -A FORWARD $dir -j ACCEPT
  done
done

# ── 4. Cilium (GKE Dataplane V2) with a unique cluster identity ──────────────
for n in $(minikube_nodes); do
  docker exec "$n" sh -c 'rm -f /etc/cni/net.d/*bridge* /etc/cni/net.d/*kindnet* /etc/cni/net.d/10-containerd*' || true
done

helm upgrade --install cilium cilium/cilium -n kube-system --kube-context "$PROFILE" \
  --set ipam.mode=kubernetes \
  --set routingMode=tunnel \
  --set tunnelProtocol=vxlan \
  --set devices=eth0 \
  --set cluster.name="$PROFILE" \
  --set cluster.id="$CLUSTER_ID" \
  --set hubble.relay.enabled=true \
  --set hubble.ui.enabled=true

kubectl --context "$PROFILE" -n kube-system rollout status ds/cilium --timeout=300s
kubectl --context "$PROFILE" -n kube-system rollout restart deploy/coredns
kubectl --context "$PROFILE" -n kube-system rollout status deploy/coredns --timeout=120s

# Label workers (control plane node keeps the bare profile name)
for n in $(minikube_nodes); do
  [ "$n" = "$PROFILE" ] && continue
  kubectl --context "$PROFILE" label node "$n" pool=main --overwrite
done

# ── 5. Registry trust on all nodes (cross-region pulls via vpc-router) ────────
for n in $(minikube_nodes); do
  docker exec "$n" bash -c "
    mkdir -p /etc/containerd/certs.d/${REGISTRY}
    cat <<EOF > /etc/containerd/certs.d/${REGISTRY}/hosts.toml
server = \"http://${REGISTRY}\"
[host.\"http://${REGISTRY}\"]
  capabilities = [\"pull\", \"resolve\", \"push\"]
  skip_verify = true
EOF"
done

echo ""
echo "[✓] Region ${REGION} is up. Verify:"
echo "    kubectl --context ${PROFILE} get nodes -o wide"
echo ""
echo "    Next (Lab 11 Step 3):"
echo "    cilium clustermesh enable --context ${PROFILE} --service-type NodePort"
echo "    cilium clustermesh connect --context acme --destination-context ${PROFILE}"
