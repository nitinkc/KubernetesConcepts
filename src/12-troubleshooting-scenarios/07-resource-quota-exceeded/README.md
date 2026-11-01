# Scenario 7: ResourceQuota Exceeded — Replica Never Created

**Silent failure.** Existing pods run fine, but the desired replica count is never
reached and no pod-level error appears.

## Reproduce
```bash
kubectl apply -f quota-demo.yml
kubectl get deploy -n quota-demo        # DESIRED 3, READY 2
kubectl get rs -n quota-demo
kubectl describe rs -n quota-demo <rs-name>
# Events: "forbidden: exceeded quota: pod-quota, requested: pods=1, used: pods=2, limited: pods=3"
```

## Fix
- Lower `replicas` to 2 in the deployment, **or**
- Raise the quota: `kubectl edit resourcequota pod-quota -n quota-demo` (`pods: "5"`).

> Tip: when running replicas < desired with no pod errors, `describe` the
> **ReplicaSet**, not the pods.
