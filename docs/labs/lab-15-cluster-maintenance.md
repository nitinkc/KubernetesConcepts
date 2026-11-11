# Lab 15 · Cluster Maintenance: PDBs, Drains & Safe Upgrades

> **Core Lesson:** Everything so far assumed nodes live forever. Real clusters drain nodes constantly — upgrades, scaling down, spot reclaim. **PodDisruptionBudgets** are the contract between "the app needs N alive" and "the platform may take pods away": without them, a routine `kubectl drain` can take your whole service down *legally*.
> **GCP Twin:** GKE node-pool upgrades run exactly this drain dance; surge upgrades + PDBs are the two knobs that keep upgrades boring.

---

## 1. Architecture Decision: Voluntary vs Involuntary Disruption

| Disruption | Examples | Defense |
| --- | --- | --- |
| **Involuntary** (node dies, OOM, preemption) | hardware failure, spot reclaim | replicas + spread (anti-affinity/topology) |
| **Voluntary** (drain, upgrade, descheduler) | `kubectl drain`, node-pool upgrade | **PDB** — the eviction API checks it first |

A PDB doesn't stop involuntary loss — it rate-limits *voluntary* eviction:

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: orders-pdb
spec:
  minAvailable: 2          # or maxUnavailable: 1 — never both
  selector:
    matchLabels:
      app: orders
```

`kubectl drain` evicts via the Eviction API → API server consults every
matching PDB → eviction allowed only while `minAvailable` stays satisfied.

> **The classic footgun:** `minAvailable: 1` on a 1-replica deployment =
> the node can NEVER drain it (drain hangs forever). PDBs must leave slack.

## 2. Step-by-Step Hands-On Build

### Step 1: Baseline — drain without a PDB (the outage nobody caused)

```bash
kubectl create deployment orders --image=nginx --replicas=3
kubectl expose deployment orders --port=80

kubectl drain <node> --ignore-daemonsets --delete-emptydir-data
# watch: all 3 orders pods evicted together → gap in service
kubectl uncordon <node>
```

### Step 2: Apply the PDB, drain again

```bash
kubectl apply -f orders-pdb.yaml          # the manifest above
kubectl get pdb orders-pdb
# NAME         MIN AVAILABLE   ALLOWED DISRUPTIONS
# orders-pdb   2               1          ← the number that matters

kubectl drain <node> --ignore-daemonsets
# eviction proceeds pod-by-pod: evict one → wait for rescheduled pod Ready
# → ALLOWED DISRUPTIONS back to 1 → evict next. Never below 2 alive.
```

### Step 3: Graceful shutdown — PDBs protect availability, not in-flight requests

```bash
# a pod being evicted gets SIGTERM → terminationGracePeriodSeconds → SIGKILL.
# in-flight requests die unless the app drains itself:
#   preStop: sleep 5      (let endpoints propagate out of the Service first)
#   + app stops accepting NEW conns while finishing old ones
```

### Step 4: Upgrade simulation (kind/minikube)

```bash
minikube node stop worker02   # node dies — involuntary: PDB does NOT help
kubectl get pods -o wide      # pods stuck Pending until nodepool replaces
# → this is why replicas + spread + PDB cover different failure shapes
```

## 3. The upgrade playbook (memorize)

```
1. cordon node      → no NEW scheduling
2. drain node       → evict pods, Eviction API respects PDBs
3. upgrade/patch    → node work
4. uncordon         → return to service
5. repeat per node  → rolling maintenance
```

On GKE the control plane automates exactly this with **surge upgrades**
(extra node stands up first so capacity never dips).

## 4. Deliberate Break & Triage

| Break | Symptom | Lesson |
| --- | --- | --- |
| PDB `minAvailable: 3` on 3 replicas | drain hangs at `ALLOWED DISRUPTIONS: 0` forever | slack is mandatory; PDB ≠ pod-protection, it's a *budget* |
| drain without `--ignore-daemonsets` | `cannot delete DaemonSet-managed pods` | daemonsets own their node; they're excluded by design |
| `kubectl delete pod` directly | bypasses PDB entirely | delete ≠ eviction — only `drain`/eviction API honors PDBs |
| probe `initialDelay` too short during drain | replacement pod goes Ready before it's warm, next eviction proceeds, brief brown-out | readiness gate must mean *actually serving* |

## 5. Verify

- [ ] `ALLOWED DISRUPTIONS` explained from memory
- [ ] You can say why PDB doesn't help a dead node (voluntary-only)
- [ ] The 5-step cordon→drain→upgrade→uncordon playbook recalled cold
- [ ] You know `maxUnavailable` vs `minAvailable` and that they're exclusive

## 6. Continue

- Lab 16 — the bigger hammer: whole-cluster backup/restore when maintenance isn't enough
- `terraform-concepts` acme GKE module — surge settings live in the node-pool config
