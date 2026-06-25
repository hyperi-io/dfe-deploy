# config/ -- config-as-code (hot-read)

dfe-* apps and dfe-engine **read this path directly** (hot-read / config-store
cascade). Argo CD does **not** apply it as k8s manifests. ClickHouse DDL is
applied from `schemas/` by a deploy Job (independent of dfe-engine).

This is everything that is config-as-code -- versioned, reviewable, promotable,
auditable. It is composed over the pinned `dfe-schemas`/built-in base (this
overlay adds/extends).

| Subdir | Holds | Written by |
|--------|-------|-----------|
| `schemas/` | custom tables/views/fieldmaps | humans + dfe-engine (generated DDL) |
| `transforms/` | VRL, Vector.dev YAML, WASM transform configs | humans + dfe-engine |
| `rules/` | detection rules | analysts + dfe-engine |
| `hunts/` | hunts | analysts + dfe-engine |
| `alerts/` | alert definitions | analysts + dfe-engine |
| `oidc/` | OIDC providers, RBAC assignments | dfe-engine |

NOT here: per-user saved searches / dashboards / preferences -- those are user
state in the app databases (HyperDX FerretDB / Valkey), never git.
