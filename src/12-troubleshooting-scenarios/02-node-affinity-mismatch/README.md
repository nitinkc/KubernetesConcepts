# Scenario 2: Node Affinity Mismatch — `Pending`

**Phase 1 (Scheduling).** `nodeSelector` requires a label no node carries.

## Reproduce
```bash
kubectl apply -f pod.yml
kubectl get pods -w          # stays Pending
kubectl describe pod affinity-pod
# Events: "0/1 nodes are available: node(s) didn't match Pod's node affinity/selector"
kubectl get nodes --show-labels   # confirm the label is missing
```

## Fix
```bash
kubectl label node <node-name> my-node=demo-node   # pod schedules immediately
# or correct/remove the nodeSelector in pod.yml
```
