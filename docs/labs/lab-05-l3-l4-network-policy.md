# Lab 05 · L3/L4 Zero-Trust Guard: Cilium NetworkPolicy & Hubble Verdicts

> **Core Lesson:** Lock down the flat pod network using **Default-Deny Ingress + Egress** in every domain namespace (`dom-orders`, `dom-payments`, `dom-inventory`) **and the `dom-data` tier**, open only the exact holes required (DNS `53`, Pod `targetPort: 8080`, and Postgres `5432`), and use **Cilium Hubble** to inspect dropped packets in real time.  
> **GCP Twin:** Phase P7e (GKE Dataplane V2 `NetworkPolicy`).

---

## 1. Architecture Decision: The 4 Non-Negotiable Rules of `NetworkPolicy`

| Rule | Why It Bites Engineers in Production |
| --- | --- |
| **1. Policies are Additive (Union of Allows)** | Once *any* `NetworkPolicy` selects a Pod for `Ingress` or `Egress`, that direction becomes **deny-by-default** except for what is matched by the union of all policies selecting that Pod. There are no `DENY` rules in standard `NetworkPolicy`. |
| **2. Both Ends of a Call Must Agree** | For `orders` (`dom-orders`) to call `payments` (`dom-payments`), you need **two** policies: an **Egress allow** in `dom-orders` AND an **Ingress allow** in `dom-payments`. Forgetting either causes a silent timeout! |
| **3. Policy Ports Are POD Ports (`8080`), Not Service Ports (`80`)** | Cilium eBPF translates `ClusterIP:80` → `PodIP:8080` **before** evaluating `NetworkPolicy`. Writing `port: 80` in your policy drops 100% of traffic! |
| **4. Default-Deny Egress Breaks Hidden Control Loops** | Blocking all egress immediately kills **CoreDNS (`53`)**, **every database connection (`5432`)**, and in later labs will kill **Istio xDS (`15012`)**, **Log Shipping (`24224`)**, and **GKE Workload Identity (`169.254.169.252:988`)**. Every platform dependency must be explicitly listed in your baseline egress policy. |
| **5. TCP Ports Don't Care About HTTP Semantics** | `NetworkPolicy` sees a raw socket. `orders → payments-db:5432` and `orders → commerce-db:5432` look *identical* at L4 (same port, same protocol) — only the **destination namespace/pod selector** separates allowed from forbidden. This is the data-isolation showcase: one wrong `namespaceSelector` and payments' private data is reachable. |

---

## 2. Visual Blueprint: Target Call Graph & Policy Matrix

![Zero-trust call graph and policy matrix](../diagrams/lab05-networkpolicy-callgraph.drawio.svg)

---

## 3. Step-by-Step Hands-On Build

### Step 1: Apply Default-Deny + DNS Baseline to All 3 Domains **and `dom-data`**

```bash
for ns in dom-orders dom-payments dom-inventory dom-data; do
kubectl apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: $ns
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: $ns
spec:
  podSelector: {}
  policyTypes:
    - Egress
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
      ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53
EOF
done
```

Test `orders -> payments` right now (before adding application allow rules):

```bash
call() {
  kubectl -n "$1" exec "deploy/$2" -c app -- sh -c "wget -O /dev/null -T 3 $3 2>&1 | tail -n1"
}

call dom-orders orders http://payments.dom-payments/ || echo "EXPECTED: Timed out by default-deny!"

# The data tier is locked too — orders can't even open a socket to its OWN database:
kubectl -n dom-orders exec deploy/orders -c app -- nc -zv -w3 commerce-db.dom-data 5432 || echo "EXPECTED: commerce-db blocked!"
```

---

### Step 2: Open Explicit East-West Paths (`orders → payments` & `orders → inventory`)

Notice how we specify **`port: 8080`** (the container's `targetPort`), **not** `80`:

```bash
# 1. Egress from dom-orders -> dom-payments and dom-inventory on TCP 8080
kubectl apply -f - <<'EOF'
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: orders-egress
  namespace: dom-orders
spec:
  podSelector:
    matchLabels:
      app: orders
  policyTypes:
    - Egress
  egress:
    - to:
        - namespaceSelector:
            matchExpressions:
              - key: kubernetes.io/metadata.name
                operator: In
                values: [dom-payments, dom-inventory]
      ports:
        - protocol: TCP
          port: 8080
EOF

# 2. Ingress into dom-payments and dom-inventory ONLY from dom-orders on TCP 8080
for d in payments inventory; do
kubectl apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-from-orders
  namespace: dom-$d
spec:
  podSelector:
    matchLabels:
      app: $d
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: dom-orders
      ports:
        - protocol: TCP
          port: 8080
EOF
done
```

---

### Step 3: Open the Data-Tier Flows (`:5432`, TCP — no HTTP here)

Same "both ends must agree" rule, but now the only discriminator is **which namespace the destination pod lives in**:

```bash
# 1. Egress to dom-data:5432 from the domains that own each DB
kubectl apply -f - <<'EOF'
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: orders-egress-data, namespace: dom-orders }
spec:
  podSelector: { matchLabels: { app: orders } }
  policyTypes: [Egress]
  egress:
    - to: [{ namespaceSelector: { matchLabels: { kubernetes.io/metadata.name: dom-data } },
             podSelector: { matchLabels: { app: commerce-db } } }]
      ports: [{ protocol: TCP, port: 5432 }]
EOF
kubectl apply -f - <<'EOF'
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: inventory-egress-data, namespace: dom-inventory }
spec:
  podSelector: { matchLabels: { app: inventory } }
  policyTypes: [Egress]
  egress:
    - to: [{ namespaceSelector: { matchLabels: { kubernetes.io/metadata.name: dom-data } },
             podSelector: { matchLabels: { app: commerce-db } } }]
      ports: [{ protocol: TCP, port: 5432 }]
EOF
kubectl apply -f - <<'EOF'
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: payments-egress-data, namespace: dom-payments }
spec:
  podSelector: { matchLabels: { app: payments } }
  policyTypes: [Egress]
  egress:
    - to: [{ namespaceSelector: { matchLabels: { kubernetes.io/metadata.name: dom-data } },
             podSelector: { matchLabels: { app: payments-db } } }]
      ports: [{ protocol: TCP, port: 5432 }]
EOF

# 2. Ingress into dom-data: commerce-db accepts orders+inventory; payments-db accepts payments ONLY
kubectl apply -f - <<'EOF'
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: commerce-db-ingress, namespace: dom-data }
spec:
  podSelector: { matchLabels: { app: commerce-db } }
  policyTypes: [Ingress]
  ingress:
    - from: [{ namespaceSelector: { matchExpressions:
               - { key: kubernetes.io/metadata.name, operator: In, values: [dom-orders, dom-inventory] } } }]
      ports: [{ protocol: TCP, port: 5432 }]
EOF
kubectl apply -f - <<'EOF'
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: payments-db-ingress, namespace: dom-data }
spec:
  podSelector: { matchLabels: { app: payments-db } }
  policyTypes: [Ingress]
  ingress:
    - from: [{ namespaceSelector: { matchLabels: { kubernetes.io/metadata.name: dom-payments } } }]
      ports: [{ protocol: TCP, port: 5432 }]
EOF
```

> **Why the extra `podSelector` on egress?** `orders → dom-data` alone would still let orders reach *payments-db* (same namespace, same port). Pinning `app: commerce-db` vs `app: payments-db` is what actually enforces data isolation — **namespace + pod** selectors are `AND`'d inside one `to:` block.

---

### Step 4: Verify the Call Matrix & Inspect Drops in Cilium Hubble

```bash
# 1. Allowed HTTP paths (Return: "remote file exists")
call dom-orders orders http://payments.dom-payments/work
call dom-orders orders http://inventory.dom-inventory/work

# 2. Allowed data-tier flows (Return: "open")
kubectl -n dom-orders    exec deploy/orders    -c app -- nc -zv -w3 commerce-db.dom-data 5432
kubectl -n dom-inventory exec deploy/inventory -c app -- nc -zv -w3 commerce-db.dom-data 5432
kubectl -n dom-payments  exec deploy/payments  -c app -- nc -zv -w3 payments-db.dom-data 5432

# 3. Forbidden Lateral Movement (Return: "wget: download timed out" / nc hangs)
call dom-payments payments http://inventory.dom-inventory/work || true
call dom-inventory inventory http://payments.dom-payments/work || true

# 4. THE SHOWCASE: orders -> payments-db:5432 — same port, same protocol,
#    same namespace as an ALLOWED flow. Only the pod selector differs -> DROPPED.
kubectl -n dom-orders exec deploy/orders -c app -- nc -zv -w3 payments-db.dom-data 5432 || true
kubectl -n dom-inventory exec deploy/inventory -c app -- nc -zv -w3 payments-db.dom-data 5432 || true

# 5. The app still works end-to-end under zero-trust — the ultimate regression test:
kubectl -n dom-orders exec deploy/orders -c app -- \
  wget -qO- --post-data='{"item_id":1,"qty":1}' \
  --header='Content-Type: application/json' http://localhost:8080/orders
# -> {"order_id":N,"status":"confirmed",...}  (HTTP hop + commerce-db tx + payments charge all allowed)

# 6. See the exact eBPF Policy Drop Verdict in Hubble!
kubectl -n kube-system exec ds/cilium -- hubble observe --verdict DROPPED --last 10
```

**Expected Hubble Output:**

```text
Oct 24 ... dom-payments/payments-xxx:41822 -> dom-inventory/inventory-xxx:8080 Policy denied DROPPED (TCP Flags: SYN)
Oct 24 ... dom-orders/orders-xxx:52914       -> dom-data/payments-db-0:5432        Policy denied DROPPED (TCP Flags: SYN)
```

> **Read the second line carefully:** that is a *TCP* drop on port `5432` — no HTTP status code, no app log, no "connection refused". At L4 the only evidence is a vanished SYN. This is why "the DB is down" is so often actually "the policy is down."

---

## 4. Deliberate Break & Triage Drills

### Drill 1: DNS-Denied vs Connection-Denied (Different Error Signatures!)

How do you know in 1 second whether `default-deny` blocked **DNS (port 53)** vs **HTTP (port 8080)**?

```bash
# Delete allow-dns in dom-orders
kubectl -n dom-orders delete netpol allow-dns

# Call payments: Notice it fails INSTANTLY with "wget: bad address 'payments.dom-payments'"!
call dom-orders orders http://payments.dom-payments/ || true

# Restore allow-dns:
kubectl apply -f - <<'EOF'
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: allow-dns, namespace: dom-orders }
spec:
  podSelector: {}
  policyTypes: [Egress]
  egress:
  - to: [{ namespaceSelector: { matchLabels: { kubernetes.io/metadata.name: kube-system } } }]
    ports: [{ protocol: UDP, port: 53 }, { protocol: TCP, port: 53 }]
EOF
```

### Drill 2: The Service Port (`80`) vs Pod Port (`8080`) Trap

```bash
# Change orders-egress port from 8080 -> 80
kubectl -n dom-orders patch netpol orders-egress --type='json' \
  -p='[{"op":"replace","path":"/spec/egress/0/ports/0/port","value":80}]'

# Call http://payments.dom-payments/ (which dials Service port 80!) -> FAILS with timeout!
call dom-orders orders http://payments.dom-payments/ || true

# Check Hubble: You see the packet was already DNAT'd to :8080 when Egress Policy evaluated it!
kubectl -n kube-system exec ds/cilium -- hubble observe --from-namespace dom-orders --verdict DROPPED --last 5

# Fix back to 8080:
kubectl -n dom-orders patch netpol orders-egress --type='json' \
  -p='[{"op":"replace","path":"/spec/egress/0/ports/0/port","value":8080}]'
call dom-orders orders http://payments.dom-payments/
```

---

## 5. Readiness Gate G-05

1. Compare the exact error messages of:
   - Missing `allow-dns` Egress policy → *`wget: bad address 'payments.dom-payments'`*
   - Missing `allow-from-orders` Ingress policy → *`wget: download timed out`*
   - Wrong `targetPort` on Service (with open policy) → *`wget: can't connect: Connection refused`*
2. On GCP GKE (`acme-labs-plan.md` P7e), what additional IP/port **must** be added to `allow-baseline-egress` in every namespace so pods can authenticate to Google Cloud APIs? *(`169.254.169.252/32` on TCP port `988` — the GKE Workload Identity metadata server).*
3. `orders` can reach `commerce-db.dom-data:5432` but not `payments-db.dom-data:5432` — same port, same protocol, same destination namespace. What exactly in the policy makes the difference? *(The `podSelector` inside the egress `to:` block pins `app: commerce-db`, and `payments-db-ingress` only admits `dom-payments`. On GCP the twin is two separate Cloud SQL instances behind one PSA range — you cannot distinguish them by CIDR, so instance-level SG-style controls don't exist; the Auth Proxy + IAM DB user is the GCP answer.)*

---
**Next Step:** [Lab 06 · L7 Zero-Trust Guard: Istio Sidecars, STRICT mTLS & SPIFFE AuthZ →](lab-06-l7-istio-mtls-authz.md)
