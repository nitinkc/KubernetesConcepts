# Scenario 1: Insufficient Resources — `Pending`

**Phase 1 (Scheduling).** The pod's resource request exceeds what any node can offer.

## Reproduce
```bash
kubectl apply -f pod.yml
kubectl get pods -w          # stays Pending
kubectl describe pod big-memory-pod
# Events: "Insufficient memory" / "Insufficient cpu"
```

## Fix
- Confirm real requirements with dev/QA, then lower `resources.requests.memory` (e.g. `512Mi`), **or**
- Add worker nodes (Cluster Autoscaler / Karpenter does this on cloud-managed clusters only).
