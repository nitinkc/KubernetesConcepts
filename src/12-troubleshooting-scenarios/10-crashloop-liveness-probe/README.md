# Scenario 10: CrashLoopBackOff — Liveness Probe Failure

**Phase 3 (Runtime).** App runs fine, but the probe command always fails;
after `failureThreshold` misses Kubernetes restarts the container forever.

## Reproduce
```bash
kubectl apply -f pod.yml
kubectl get pods -w                # Running, then restart every ~30s
kubectl describe pod liveness-pod  # Events: "Liveness probe failed: ls: /tmp/l: No such file"
kubectl get pod liveness-pod       # RESTARTS counter keeps climbing
```

## Fix
- Point the probe at a real health check (e.g. `httpGet: {path: /, port: 80}`), or
- Fix the app so the check succeeds.
> Always `kubectl logs liveness-pod` before blaming the probe — it may be
> masking a genuine app problem.
