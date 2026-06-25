# dfe-deploy -- DFE per-environment deploy repo (template / seed)

This repository is the **template** for a DFE deployment's git store. It is **not**
used directly. Each deployment instantiates its **own read-write copy**, which
becomes that environment's deployment source of truth.

> Canonical model + diagrams: `dfe-docs/deployment/state-and-repos.md`.

## What this is

The "one throat to choke" for a single DFE environment. It holds everything that
is **created/local** to a deployment, and **references** the HyperI-provided base
(`dfe-infra`, `dfe-schemas`) by pinned version -- it never vendors them in.

```
dfe-deploy/                 # RW -- yours, per environment, survives base updates
  pins.yaml                 # pinned dfe-infra + dfe-schemas versions (the base, by reference)
  infra/                    # Argo-WATCHED overlay: scaling, enablement, cloud specifics
  config/                   # HOT-READ config-as-code (apps + dfe-engine read this)
    schemas/                #   custom schemas
    transforms/             #   VRL / Vector / WASM transform configs
    rules/  hunts/  alerts/ #   detection content
    oidc/                   #   OIDC providers / RBAC assignments
```

Per-user UI state (saved searches, dashboards, prefs) does **not** live here --
it lives in the app databases (HyperDX FerretDB / Valkey).

## How a real deployment uses it

Seed once, owned thereafter:

- **Self-contained / air-gapped (default):** `dfe-infra` bootstrap seeds an
  **in-cluster Gitea** repo from this template. Argo CD, dfe-engine and operators
  read/write that in-cluster repo.
- **GitHub/GitLab-hosted:** use this template ("Use this template") to create your
  own `dfe-deploy` repo; point Argo CD + dfe-engine at it.

## Who writes what

| Path | Written by | Read by |
|------|-----------|---------|
| `pins.yaml` | ops (bump to update base) | bootstrap / Argo |
| `infra/` | ops (GA); dfe-engine app-params (v+0.1) | Argo CD |
| `config/` | dfe-engine + analysts | dfe-* apps + dfe-engine (hot-read); ClickHouse (DDL apply Job) |

dfe-engine writes **only** this repo, by commit (auditable), and never the base.

## Updating the base

Bump the versions in `pins.yaml`. Your `infra/` and `config/` are untouched. The
base (`dfe-infra`, `dfe-schemas`) is pulled by reference at the pinned version
(Argo multi-source / Helm dependency / OCI) -- never copied in, never a submodule.

---

License: LicenseRef-HyperI-Proprietary -- (c) 2026 HYPERI PTY LIMITED
