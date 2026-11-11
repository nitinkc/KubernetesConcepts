
## Install minikube

```shell
brew install minikube

minikube start
minikube dashboard

minikube dashboard --url
minikube dashboard --port=8080

minikube addons enable metrics-server


minikube addons enable yakd
minikube service yakd-dashboard -n yakd-dashboard

```

## Clean Reset

```shell
# Completely delete the existing cluster and its configuration cache
minikube delete --all --purge

# Start a completely fresh cluster
minikube start --driver=docker

```

## Local Setup

```shell
uv venv
uv pip install -r requirements.txt
```

```shell
task --list
```

| Task | Runs |
| --- | --- |
| `lab01:up` / `lab01:routes` / `lab01:firewall` | Docker networks, router/probe/registry/echo, routes, FORWARD rules — all idempotent |
| `lab02:up` | `minikube start` + routes + Cilium + node labels (deps chain does it in order) |
| `lab03:images` / `lab03:chart` / `lab03:data` / `lab03:domains` | Builds, vendored chart copy + lint, StatefulSets + seed, 3 helm installs |
| `lab04:close-doors` / `lab04:restore` | Egress-cut helpers |
| `lab06:istio` / `lab08:metallb` / `lab09:flux` | One-shot installs |
| `lab11:region` / `lab11:us-id` / `lab11:mesh` | `task lab11:region REGION=asia OCTET=12 ID=3` |
| `status` / `routes` / `fixctx` / `stop` / `start` / `clean` / `verify:all` | Lifecycle + the triage signatures (#03 routes reset, #31 stale tunnel) |

Two deliberate design choices:

clean asks for confirmation via Task's prompt: — it deletes all five profiles.
Break/restore drills are not tasks — heredoc policies, iptables edits, and route deletion are the lesson; they stay manual in the docs. The Taskfile covers provisioning, not the deliberate-break exercises.
Given your current broken acme profile, the path is: task clean → task lab01:up lab01:routes lab01:firewall → task lab02:up → verify with task status.
