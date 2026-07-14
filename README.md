# dfe-deploy -- DFE per-environment deploy repo (template / seed)

This repository is the **template** for a DFE deployment's git store. It is **never**
used directly as a live deploy repo - not by any customer and not by HyperI's own
environments. Each deployment instantiates its **own read-write copy** (fork,
"Use this template", or a bootstrap-seeded in-cluster clone), which becomes that
environment's deployment source of truth.

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
    sources/                #   source definitions (all-in-one doc, gitcrud `sources` class)
    schemas/                #   custom schemas
    transforms/             #   VRL / Vector / WASM transform configs
    rules/  hunts/  alerts/ #   detection content
    oidc/                   #   OIDC providers / RBAC assignments
```

Per-user UI state (saved searches, dashboards, prefs) does **not** live here --
it lives in the app databases (HyperDX FerretDB / Valkey).

## How a real deployment uses it

Seed once, owned thereafter. Three supported paths, in order of preference:

1. **Bootstrap-seeded in-cluster repo (default, air-gap safe):** `dfe-infra`
   bootstrap seeds this template -- at the stack release's matching tag -- into
   the bundled **in-cluster Forgejo**. Argo CD, dfe-engine and operators
   read/write that repo.
2. **Forge template copy (GitHub/GitLab-hosted):** GitHub "Use this template"
   (the flag is set on this repo) or GitLab "new from template" -- fresh
   private repo, clean history, no upstream lineage.
3. **Clone and re-home (any forge / manual):** clone at the release tag, remove
   `origin`, push to your own remote.

**Never FORK this repo.** A fork of a public repo cannot be private (your
deploy repo carries your config), and fork lineage invites merge-from-upstream
-- but base updates arrive by bumping `pins.yaml`, never by merging template
history. Full rationale + the stack-version model:
`dfe-docs/deployment/state-and-repos.md` and
`dfe-docs/deployment/stack-versioning.md`.

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
