# Scenario 11: CrashLoopBackOff — Init Container Failure

**Phase 3 (Runtime).** Init containers must exit 0 before the main container
starts. A failing init container means the app container is never reached.

## Reproduce
```bash
kubectl apply -f pod.yml
kubectl get pods -w                    # Init:CrashLoopBackOff
kubectl describe pod init-fail-pod     # init container restarting
kubectl logs init-fail-pod -c init-setup   # read init container logs
```

## Fix
Fix the init container's command/image so it completes successfully
(e.g. `echo 'init done'` instead of `exit 1`).
