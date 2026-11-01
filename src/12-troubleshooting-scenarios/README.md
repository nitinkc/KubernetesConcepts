# Kubernetes Troubleshooting Scenarios

13 intentionally broken manifests, grouped by pod lifecycle phase.
Each folder has the broken YAML plus a README with reproduce → diagnose → fix.

## The 3 phases

| Phase | What happens | Status you'll see |
|---|---|---|
| 1. Scheduling | Pod assigned to a node | `Pending` |
| 2. Container creation | Image pulled, volumes mounted | `ContainerCreating` / `ErrImagePull` / `ImagePullBackOff` |
| 3. Runtime | App runs the startup command | `Running` / `CrashLoopBackOff` |

## Universal first steps
```bash
kubectl get pods -w                  # which phase is it stuck in?
kubectl describe pod <name>          # read the Events section
kubectl logs <pod> [-c <container>]  # phase 3 / app-level errors
```

## Scenarios

| # | Folder | Symptom | Root cause |
|---|---|---|---|
| 1 | `01-insufficient-resources` | Pending | request > node capacity |
| 2 | `02-node-affinity-mismatch` | Pending | nodeSelector label missing on all nodes |
| 3 | `03-unbound-pvc` | Pending | PVC can't bind (no PV / StorageClass) |
| 4 | `04-node-taint-no-toleration` | Pending | node taint, no toleration in spec |
| 5 | `05-missing-configmap` | ContainerCreating | ConfigMap volume doesn't exist |
| 6 | `06-missing-secret` | ContainerCreating | Secret volume doesn't exist |
| 7 | `07-resource-quota-exceeded` | replicas < desired, silent | namespace ResourceQuota — describe the RS |
| 8 | `08-imagepullbackoff` | ImagePullBackOff | bad image tag / missing pull secret |
| 9 | `09-crashloop-oom` | CrashLoopBackOff | OOMKilled — limit < usage |
| 10 | `10-crashloop-liveness-probe` | CrashLoopBackOff | probe command always fails |
| 11 | `11-crashloop-init-container` | Init:CrashLoopBackOff | init container exits non-zero |
| 12 | `12-crashloop-app-runtime` | CrashLoopBackOff | app error (e.g. DB unreachable) — check logs |
| 13 | `13-service-label-mismatch` | Running but unreachable | Service selector ≠ pod labels → no endpoints |

> Try to fix each scenario yourself before reading the README's Fix section.
