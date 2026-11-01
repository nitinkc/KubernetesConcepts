# Scenario 6: Missing Secret — `ContainerCreating`

**Phase 2 (Container Creation).** Same as Scenario 5 but for a Secret volume.

## Reproduce
```bash
kubectl apply -f pod.yml
kubectl get pods -w               # stuck at ContainerCreating
kubectl describe pod secret-pod   # Events: secret "my-password" not found
kubectl get secret                # confirm it is missing
```

## Fix
```bash
kubectl create secret generic my-password --from-literal=password='s3cr3t'
```
