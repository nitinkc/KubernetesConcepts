# Scenario 4: Node Taint Without Toleration — `Pending`

**Phase 1 (Scheduling).** The node is tainted; the pod lacks a matching toleration.

## Reproduce
```bash
kubectl taint nodes minikube taint=true:NoSchedule
kubectl apply -f pod.yml
kubectl get pods -w               # stays Pending
kubectl describe pod tainted-pod  # Events: node(s) had untolerated taint
kubectl describe node minikube | grep -i taint
```

## Fix
Uncomment the `tolerations` block in `pod.yml` and re-apply, or remove the taint:
```bash
kubectl taint nodes minikube taint=true:NoSchedule-
```
