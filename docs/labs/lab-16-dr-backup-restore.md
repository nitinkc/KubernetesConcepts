# Lab 16 · Disaster Recovery: Backup & Restore with Velero

> **Core Lesson:** Every lab rebuilds *forward* (lab 10 cold rebuild). DR assumes you can't: etcd corrupts, a namespace gets `kubectl delete`d, a region fails. **Velero** snapshots cluster resources (+ PV data) to object storage and restores them — and the drill that matters is the **restore**, not the backup.
> **GCP Twin:** Velero on GKE with a GCS bucket + Workload Identity is the standard pattern; Cloud SQL has its own PITR — know which tool owns which layer.

---

## 1. Architecture Decision: What Does "Backup" Even Mean?

| Layer | Owned by | Restores |
| --- | --- | --- |
| Cluster resources (deployments, secrets, RBAC) | **Velero** (or GitOps repo!) | deleted objects, config drift |
| PV data | Velero + restic/CSI snapshots | volume contents |
| Managed DB data | **Cloud SQL PITR / backups** (NOT velero) | DB to point-in-time |
| Desired state | **your GitOps repo** | the *best* restore: re-apply everything |

> **The senior-engineer answer:** GitOps IS your resource backup —
> `flux reconcile` rebuilds resources. Velero covers what git doesn't:
> cluster-created objects, PV data, and the world *between* commits.

| RPO (how much data can you lose?) | RTO (how fast back?) | Design consequence |
| --- | --- | --- |
| hours | hours | daily velero schedule is fine |
| minutes | minutes | CSI snapshots + tested restore runbook |
| zero | minutes | multi-region + replication (lab 11) — backup alone can't get there |

## 2. Step-by-Step Hands-On Build

### Step 1: Install Velero with local object storage

```bash
# minio as the local "GCS bucket"
helm install velero vmware-tanzu/velero \
  -n velero --create-namespace \
  --set deployNodeAgent=true \
  --set configuration.backupStorageLocation[0].provider=aws \
  --set configuration.backupStorageLocation[0].bucket=velero \
  --set configuration.backupStorageLocation[0].config.region=minio \
  --set configuration.backupStorageLocation[0].config.s3Url=http://minio.velero.svc:9000
# (GCP: provider=gcp + bucket + WI — same object model)
```

### Step 2: Create state worth losing, then back it up

```bash
kubectl create ns dr-demo
kubectl -n dr-demo create deployment app --image=nginx --replicas=2
kubectl -n dr-demo create configmap keepme --from-literal=data=precious

velero backup create dr-demo-backup --include-namespaces dr-demo --wait
velero backup describe dr-demo-backup   # Phase: Completed — objects + metadata in the bucket
```

### Step 3: The drill — delete the namespace, restore it

```bash
kubectl delete ns dr-demo              # the disaster
kubectl get ns dr-demo                 # gone

velero restore create --from-backup dr-demo-backup --wait
kubectl -n dr-demo get deploy,cm       # app + keepme are back
```

### Step 4: Scheduled backups + expiry

```bash
velero schedule create daily --schedule="0 2 * * *" \
  --include-namespaces dr-demo --ttl 72h
velero schedule get                    # backup cadence = RPO dial
```

## 3. Deliberate Break & Triage

| Break | Symptom | Lesson |
| --- | --- | --- |
| Restore into existing (non-deleted) namespace | conflicts: objects skipped/patched per `existingResourcePolicy` | restore ≠ merge; decide overwrite semantics ahead of time |
| Backup with `--ttl 24h`, check day 2 | backup object auto-expired/deleted | TTL is the retention dial — auditors ask for it by name |
| Backup exists but bucket creds expired | `BackupStorageLocation` → Unavailable | the storage location is a first-class CR — check it first |
| Restore PVs without snapshot plugin | pod stuck Pending — no volume data | resources ≠ data; PV restore needs restic/CSI/GCE-disk snapshots |

## 4. The DR runbook skeleton (write it in the drill)

```
1. Detect: what layer failed? (object / PV / DB / cluster / region)
2. Restore target: GitOps re-apply (preferred) → velero restore → DB PITR
3. Verify: app health + data spot-checks, not just "restore completed"
4. Postmortem: why did we need the restore? (that's the real finding)
```

## 5. Verify

- [ ] You restored a deleted namespace and proved data integrity
- [ ] You can state which layer velero does NOT cover (managed DB data)
- [ ] RPO vs RTO in one sentence each, and which dial controls each
- [ ] You can argue "GitOps is the first restore path" credibly

## 6. Continue

- Lab 10's cold-rebuild script = forward-path DR for this very lab cluster
- `terraform-concepts` acme cloudsql root — managed-DB backup is a TF resource, not velero
