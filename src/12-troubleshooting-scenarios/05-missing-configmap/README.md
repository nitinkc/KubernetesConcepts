# Scenario 5: Missing ConfigMap — `ContainerCreating`

**Phase 2 (Container Creation).** Pod is scheduled, but the volume mount fails
because the referenced ConfigMap doesn't exist.

## Reproduce
```bash
kubectl apply -f pod.yml
kubectl get pods -w                 # Pending -> ContainerCreating (stuck)
kubectl describe pod configmap-pod  # Events: configmap "my-map" not found
kubectl get cm                      # confirm it is missing
```

## Fix
```bash
kubectl create configmap my-map --from-literal=app.conf="env=prod"
# pod proceeds to Running once the ConfigMap exists
```
