# Lab 17 · Access & Admission: RBAC, TLS Certificates, and Operators

> **Core Lesson:** Three "last mile" production controls in one lab: **RBAC** answers *who may call the API* (labs used cluster-admin — unacceptable in prod); **cert-manager** answers *where TLS certs come from* (lab 08's ingress terminated TLS by hand); **operators/CRDs** answer *how Kubernetes itself gets extended* — Flux, ESO, cert-manager and Flagger are all operators you've already used without naming the pattern.
> **GCP Twin:** RBAC↔IAM binding is the same least-privilege story as `iam.tf`; cert-manager ↔ GKE managed certs.

---

## 1. RBAC: from cluster-admin to least privilege

The objects in one breath: `Role`/`ClusterRole` = permission *sets*
(verb + resource); `RoleBinding`/`ClusterRoleBinding` = permission *grants*
(set + subject + scope).

```bash
# A read-only developer role, namespace-scoped:
cat << 'EOF' | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata: {name: app-reader, namespace: dom-apps}
rules:
  - apiGroups: ["", "apps"]
    resources: [pods, pods/log, deployments, services]
    verbs: [get, list, watch]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata: {name: dev-read-dom-apps, namespace: dom-apps}
subjects:
  - kind: ServiceAccount
    name: dev-user
    namespace: dom-apps
roleRef:
  kind: Role
  name: app-reader
  apiGroup: rbac.authorization.k8s.io
EOF

# prove it — impersonation is the debugging superpower:
kubectl auth can-i list pods -n dom-apps --as=system:serviceaccount:dom-apps:dev-user
# yes
kubectl auth can-i delete pods -n dom-apps --as=system:serviceaccount:dom-apps:dev-user
# no   ← least privilege verified, not assumed
```

| RBAC instinct to build | Why |
| --- | --- |
| `Role` + `RoleBinding` (namespaced) default; `ClusterRole*` only for cluster objects (nodes, CRDs, namespaces) | cluster-scoped grants are blast-radius multipliers |
| `kubectl auth can-i --as=` before granting | verify the grant, don't assume it |
| Secrets access = separate decision | `get secrets` in a namespace ≈ read-all-credentials |

## 2. cert-manager: TLS as a reconciled object

Replace the hand-rolled cert from lab 08 with the issuer→certificate flow:

```bash
helm install cert-manager jetstack/cert-manager -n cert-manager \
  --create-namespace --set crds.enabled=true
```

```yaml
# ClusterIssuer = the CA plumbing (selfSigned for lab; ACME/Let's Encrypt or
# a private CA in real estates)
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata: {name: lab-ca}
spec:
  selfSigned: {}
---
apiVersion: cert-manager.io/v1
kind: Certificate                  # the request — cert-manager does the rest
metadata: {name: ingress-tls, namespace: dom-apps}
spec:
  secretName: ingress-tls-secret   # ← lands here as a real tls Secret
  dnsNames: [app.acme.local]
  issuerRef: {name: lab-ca, kind: ClusterIssuer}
```

`kubectl get certificate` shows `READY: True` → the `ingress-tls-secret`
exists → wire it into the lab-08 `Ingress` `tls:` block. Renewal is
automatic before expiry — that's the point: certs become a reconciled
object, not a calendar reminder.

## 3. Operators & CRDs: the pattern under everything

```bash
kubectl get crd | grep -E "cert-manager|external-secrets|flagger|fluxcd"
```

You've used operators all along: a **CRD** declares a new API object
(`Certificate`, `ExternalSecret`, `Canary`); an **operator** is the
controller loop reconciling it toward desired state. Kubernetes is
programmable — the pattern you're now qualified to build with
kubebuilder/operator-sdk when a CRD you need doesn't exist.

**Admission controllers** are the other hook: mutating (Istio's sidecar
injector — lab 06!) vs validating (lab 18's policy engine). You finally
have the full control-loop mental model.

## 4. Deliberate Break & Triage

| Break | Symptom | Lesson |
| --- | --- | --- |
| RoleBinding in wrong namespace | `can-i` returns `no` despite correct Role name | bindings are scoped to their own namespace |
| Certificate `READY: False` | `describe certificate` shows issuer mismatch or bad dnsName | cert issues surface as events on the Certificate, not pod logs |
| `kubectl delete crd certificates.cert-manager.io` | every Certificate + managed secret orphaned/deleted | CRD deletion cascades — it's why infra CRDs are tier-0 in lab 09 |
| Grant `get secrets` to dev-user SA | can now read every secret in namespace | secrets RBAC is a separate trust boundary from pods RBAC |

## 5. Verify

- [ ] `auth can-i --as=` used to *prove* least privilege
- [ ] A Certificate reconciled into a usable ingress TLS secret
- [ ] You can name: CRD declares, operator reconciles, admission intercepts
- [ ] The three objects chain cold: Role (permissions) → RoleBinding (grant) → subject

## 6. Continue

- Lab 18 — validating admission at scale: Kyverno policies enforcing the rules this lab granted
