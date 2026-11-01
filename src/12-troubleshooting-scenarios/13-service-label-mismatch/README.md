# Scenario 13: Pod Running but App Not Accessible — Service Label Mismatch

Pods are healthy, yet the Service can't reach them: its selector doesn't match
any pod labels, so it has **zero endpoints**.

## Reproduce
```bash
kubectl apply -f app.yml
kubectl get pods -o wide                    # both Running
kubectl get endpoints web-service           # <none> — the smoking gun
kubectl describe svc web-service            # Endpoints: <none>
# direct pod IP works, ClusterIP does not:
kubectl port-forward deploy/web-app 8080:80 # works fine
```

## Fix
Make the Service selector match the pod label:
```yaml
spec:
  selector:
    app: web-frontend   # was 'web-store'
```
Then `kubectl get endpoints web-service` shows both pod IPs.

## Debug path for "app not accessible"
1. Can you reach the pod IP directly? → app/pod fine.
2. Does the Service have endpoints? → selector/label mismatch.
3. LoadBalancer type? → check cloud security groups / ingress rules.
