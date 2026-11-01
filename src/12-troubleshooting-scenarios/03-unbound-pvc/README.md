# Scenario 3: Unbound PersistentVolumeClaim — `Pending`

**Phase 1 (Scheduling).** The pod references a PVC that can never bind: no matching
PV exists and the `manual` StorageClass doesn't exist for dynamic provisioning.

## Reproduce
```bash
kubectl apply -f app.yml
kubectl get pvc              # data-claim stays Pending
kubectl get pods -w          # pvc-pod stays Pending
kubectl describe pod pvc-pod # Events: "pod has unbound immediate PersistentVolumeClaims"
```

## Fix — create a static PV
```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: data-pv
spec:
  storageClassName: manual        # must match the PVC
  capacity: { storage: 1Gi }
  accessModes: [ReadWriteOnce]
  hostPath: { path: /tmp/data }   # minikube/local only
```
Alternative: remove `storageClassName` so the default StorageClass provisions
dynamically. On cloud, a StorageClass backed by EBS/GCE PD is the real fix.
