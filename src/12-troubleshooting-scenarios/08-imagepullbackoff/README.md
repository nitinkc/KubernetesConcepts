# Scenario 8: ImagePullBackOff

**Phase 2 (Container Creation).** Scheduled fine, but the image can't be pulled.

## Reproduce
```bash
kubectl apply -f pod.yml
kubectl get pods -w                # ErrImagePull -> ImagePullBackOff
kubectl describe pod bad-image-pod
# Events: "Failed to pull image nginx:latstt: not found"
```

## Fix
Correct the image name/tag in `pod.yml` (`nginx:latest` or a real tag).
For private registries: create an `imagePullSecret` and reference it via
`spec.imagePullSecrets`.
