# Scenario 12: CrashLoopBackOff — Application Runtime Error

**Phase 3 (Runtime).** Scheduling, pull, and container creation all succeed —
then the app itself crashes (simulated: JDBC connection failure to MySQL).

## Reproduce
```bash
kubectl apply -f pod.yml
kubectl get pods -w               # CrashLoopBackOff
kubectl logs app-crash-pod        # "Connection refused" to jdbc:mysql://mysql-svc
kubectl describe pod app-crash-pod
```

## Fix (real-world causes)
- Database is down or unreachable — deploy/verify the `mysql-svc` Service.
- Wrong connection string (host, port, credentials).
- DB connection limit reached — work with the DBA team.
