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
(`dfe-infra`) by pinned version -- it never vendors it in.

```
dfe-deploy/                 # RW -- yours, per environment, survives base updates
  pins.yaml                 # pinned dfe-infra version (the base, by reference)
  values/                   # Argo-WATCHED helm values: ONE file per service instance
                            #   ({service}-{instance}-values.yaml; file presence = app enabled)
  config/                   # HOT-READ config-as-code (apps + dfe-engine read this)
    sources/                #   source definitions (all-in-one doc, gitcrud `sources` class)
    schemas/                #   this deployment's additive schema overlay
    transforms/             #   VRL / Vector / WASM transform configs
    rules/  hunts/  alerts/ #   detection content
    oidc/                   #   OIDC providers / RBAC assignments
```

Per-user UI state (saved searches, dashboards, prefs) does **not** live here --
it lives in the app databases (HyperDX FerretDB).

## How a real deployment uses it

Seed once, owned thereafter. Three supported paths, in order of preference:

1. **Bootstrap-seeded in-cluster repo (default, air-gap safe):** `dfe-infra`
   bootstrap stands up the bundled **in-cluster Forgejo** and creates the deploy
   repo; this template -- at the stack release's matching tag -- seeds it
   (automated seeding lands with the first tagged stack release). Argo CD,
   dfe-engine and operators read/write that repo.
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
| `values/` | ops AND dfe-engine - the SAME per-service files (hard standard: the only helm-values home; see `values/README.md`) | Argo CD |
| `config/` | dfe-engine + analysts | dfe-* apps + dfe-engine (hot-read). `config/schemas/` is the engine's schema overlay, applied by the engine at startup -- there is no DDL Job |

dfe-engine writes **only** this repo, by commit (auditable), and never the base.

## Updating the base

Bump the version in `pins.yaml`. Your `values/` and `config/` are untouched. The
base (`dfe-infra`) is pulled by reference at the pinned version (Argo
multi-source / Helm dependency / OCI) -- never copied in, never a submodule. The
schema release moves with the dfe-engine image that stack pins, because the
`dfe-schemas` wheel rides inside it.

---

Licensed under BUSL-1.1 - see [LICENSE](LICENSE). (c) 2026 HYPERI PTY LIMITED

## Context

Depth, and the reasoning behind the shape: [docs/architecture.md](docs/architecture.md).

### What this is

The template a deployment's git store is seeded FROM -- never itself a live
deploy repo, so nothing here is reconciled to a cluster. A deployment takes its
own read-write copy and Argo CD, dfe-engine and operators read and write that.
Not the base either: charts and ApplicationSets live in dfe-infra, pulled by
reference at the `pins.yaml` tag. One validator aside, there is no code here and
no Kubernetes manifest.

### Where things live

| Path | Holds |
|---|---|
| `pins.yaml` | the dfe-infra tag selecting the whole certified stack, the release `channel`, per-component `overrides` |
| `values/` | one `{service}-{instance}-values.yaml` per APP instance -- file presence enables the app |
| `infra/` | `common.yaml` plus one `<chart>.yaml` per data or platform chart |
| `config/` | hot-read config-as-code: `sources/`, `schemas/`, `transforms/`, `rules/`, `hunts/`, `alerts/`, `oidc/` |
| `governance/` | five curated dials in `actions/`, protected-var patterns in `policies/` |
| `tools/validate_governance.py` | the structural validator for `governance/` |

Every directory carries its own README. Read `values/README.md` and
`infra/README.md` before a first edit.

### Commands that prove a change

```bash
python3 tools/validate_governance.py
```

The whole local gate: schema shape, closed param constraints, reference wiring
and the guard against an action changing a governance class. How it lies:

- `validate-governance.yaml` filters `paths:` on BOTH `push` and `pull_request`,
  to `governance/**` and the two `tools/` files. A PR touching only `values/`,
  `config/`, `pins.yaml` or a README shows no checks -- did not run, not passed.
- `release.yaml` carries no path filter and re-runs the gate before tagging, so a
  docs change is checked on merge rather than in review. semantic-release exits 0
  either way, so it reads `git tag --points-at HEAD` instead.
- Nothing validates `values/`, `infra/` or `config/`. Chart-var drift belongs to
  dfe-infra's chart validation, and a typo in an instance file surfaces in Argo.

### What tends to bite

| Don't | Do | Why |
|---|---|---|
| Park YAML under `values/`, subdirectories included | Put anything that is not an app instance in `infra/` | Argo hands the `values/*-values.yaml` glob to `git ls-files` as a pathspec, where `*` matches `/` -- so a subdirectory file becomes a phantom Argo app (`99289a4`, `976a898`) |
| Fork this repo | Use the template, or clone at the tag and re-home | A fork of a public repo cannot be private, and base updates arrive by bumping `pins.yaml`, never by merging template history (`9b800f1`) |
| Omit `deploy:` from an instance file | Name `deploy.service` and `deploy.instance` | The ApplicationSet reads it to name the Application, so the file yields no app and no error (`1874994`) |
| Expect a Job to apply `config/schemas/` | Treat it as the engine's additive overlay | There is no Job -- the engine applies every object at its own startup. `config/README.md` claimed one until `e3b2ca9` (#4) |
| Read `OK: 0 action(s)` as a pass | Check the count is non-zero | `--root` once defaulted to `.`, so a run from the wrong directory reported success having checked nothing |
| Deploy `dfe-receiver` untouched | Set `loadBalancerSourceRanges`, or `config.server.auth.mode` | It ships `exposure.mode: public` with an EMPTY allow-list, and empty means `0.0.0.0/0`. `auth.mode` defaults to `none` (`7cae6f6`) |

### Where this sits

| Repo | Direction | Kind | Mechanism |
|---|---|---|---|
| dfe-infra | inbound | `version-pin` | `pins.yaml` `base.dfe-infra` names one tag whose `versions.yaml` is the manifest for every app image, operator and data service. Pulled by reference, never vendored. `pins.yaml` also calls `dfe-infra/scripts/dfe-stack` by path. Move it, then re-run the validation |
| dfe-schemas | inbound | none | No pin, deliberately, since `e3b2ca9` (2026-09-18). The wheel rides inside the dfe-engine image, so the dfe-infra pin already selects the schema release |
| dfe-infra | outbound | `version-pin` | `versions.yaml` `content.dfe-deploy` pins this repo's tag per stack and bootstrap seeds from it, so a change lands in a deployment only once a stack pins a newer tag |
| dfe-engine | outbound | commits into a copy | Writes a deployment's COPY through gitcrud -- `helmvars` for `values/`, `governance/`, and the config classes. Never the base, never this repo. Not declared in `dfe-infra/suite.yaml` |
