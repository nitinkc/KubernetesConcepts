---
type: agents_instructions
title: "KubernetesConcepts — Agent Instructions"
description: "Network-first Kubernetes learning platform: MkDocs lab site (Acme Labs, Docker→Minikube→GKE) plus a src/ manifest and troubleshooting-scenario library"
tags: ["kubernetes", "mkdocs", "gke", "learning-labs"]
component: project
source_paths: ["."]
timestamp: "2026-10-31"
author: "codebase-context-builder"
version: "1.0"
---

# KubernetesConcepts — Agent Instructions

> 10 hands-on labs (Docker underlay → Minikube/Cilium → Istio → Flux → Terraform → GKE handoff) where every local construct maps 1:1 to a GCP twin, plus `src/` manifest & troubleshooting-scenario libraries.

## Knowledge Base

All project context lives in `docs/`. Start with the context index, then load only
the pages relevant to the current task.

| Resource | Path | Purpose |
| ---------- | ------ | --------- |
| Schema & agent workflows | [docs/README.md](docs/README.md) | Read when maintaining the knowledge base |

## Quick Reference

See [docs/context/agents/quick-reference.md](docs/context/agents/quick-reference.md).

## Expertise

- Kubernetes networking depth: CNI/IPAM (Cilium, `ipam.mode=kubernetes`), NetworkPolicy vs DNAT ordering, CoreDNS, egress paths
- The local↔GCP twin model: Docker bridge ⇄ VPC, `vpc-router`/`iptables` ⇄ routes+firewall, MetalLB ⇄ Gateway/NEG, Flux tiers ⇄ GitOps repo
- MkDocs Material authoring: nav, plugins (quiz, mermaid2, glightbox), `pymdownx` extensions, `--strict` builds
- The repo's pedagogy: 4-step Architect's Loop, `> **GCP Twin:**` headers, shared 10.10/10.20/10.30 IPAM

## Debugging Rules

1. **Trace from entry points** — for docs: `mkdocs.yml` nav → page → embedded diagram; for manifests: `kubectl apply` order → describe → logs
2. **Git diffs required** — analyze the FULL diff when files recently changed (several `src/` dirs are untracked/modified)
3. **Never theorize** — read the actual file; lab prose occasionally contains unformatted pasted notes
4. **Match symptom to layer** — use `docs/reference/02-failure-triage-matrix.md` before suggesting fixes
5. **Submodule awareness** — `.git` is a file; run git from repo root only

## Code Quality

- **Maintain the context artifacts in the same commit.** Update the owning `docs/context/`
  page(s), `docs/progress/features.json`, and `.devin/wiki.json` as part of the change
  that touches architecture, components, or feature status. For significant changes,
  append a dated entry to `docs/progress/log.md`. Do not defer these updates.
- Verify docs changes with `mkdocs build --strict` before committing.
- Keep the shared IPAM (`docs/reference/00-architecture-decisions.md`) consistent — it is load-bearing across all labs.

## Hard Rules

See [docs/context/agents/hard-rules.md](docs/context/agents/hard-rules.md).

## Pending Work

> See [docs/progress/features.json](docs/progress/features.json) for full status.

- `troubleshooting-scenarios`, `10-hpa-vpa`, `terraform-k8s.md` — complete on disk, **untracked in git**
- `gcp-execution` — P0–P10 GCP build is planned, not started
- `rebuild-scripts` — `cluster-up.sh`/`verify-all.sh` live outside the repo; committing them is open
- `repo-hygiene` — stale `repo_url`, duplicate glightbox pin, stray `diagrams/` dir, empty `src/11-stateful-set/`

## Debugging Tips

See [docs/context/agents/debugging-tips.md](docs/context/agents/debugging-tips.md).
