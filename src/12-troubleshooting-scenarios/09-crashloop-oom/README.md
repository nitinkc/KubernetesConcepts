# Scenario 9: CrashLoopBackOff — Out of Memory (OOMKilled)

**Phase 3 (Runtime).** Container starts, exceeds `limits.memory`, gets killed,
and Kubernetes keeps restarting it.

## Reproduce
```bash
kubectl apply -f pod.yml
kubectl get pods -w          # Running -> OOMKilled -> CrashLoopBackOff
kubectl describe pod oom-pod # Last State: OOMKilled
```

## Fix
Determine real memory needs (metrics, dev/QA), then raise `limits.memory`
above actual usage (e.g. `300Mi` for this 250M workload).
