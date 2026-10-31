# config/ -- config-as-code (hot-read)

dfe-* apps and dfe-engine **read this path directly** (hot-read / config-store
cascade). Argo CD does **not** apply it as k8s manifests. No Job here applies
ClickHouse DDL: dfe-engine is the only thing that creates a database, table,
view, role or Kafka topic, and it does it at its own startup.

This is everything that is config-as-code -- versioned, reviewable, promotable,
auditable. It is composed over the pinned `dfe-schemas`/built-in base (this
overlay adds/extends).

| Subdir | Holds | Written by |
|--------|-------|-----------|
| `sources/` | source definitions (all-in-one doc, gitcrud `sources` class) | humans + dfe-engine |
| `schemas/` | this deployment's own schema overlay -- see below -- and `derived/`, the column selections sources name | humans + dfe-engine |
| `rules/` | detection rules, read by the hunt runner | analysts + dfe-engine |
| `hunts/` | hunts, read by the hunt runner | analysts + dfe-engine |

The engine also creates `compat-profiles/` and `library/` here on first write.

NOT here: per-user saved searches / dashboards / preferences -- those are user
state in the app databases (HyperDX FerretDB), never git. Transform files are
inline in the instance file (`fileSets.transforms.files`, see `values/README.md`).
Alert destinations live on the engine's config volume, OIDC providers in the
engine's auth directory, and RBAC accounts, groups and roles under `governance/`.

## `schemas/` -- the deployment's own overlay

The core schema is the `dfe-schemas` wheel pinned inside the dfe-engine image,
read-only. This directory is the second tree, and it is **additive**: it may
declare objects the core does not, and it may never redefine one the core does.

No chart sets `DFE_SCHEMAS_OVERLAY_DIR`, so the engine ignores this directory
until the engine's instance file points it at the engine's clone of this repo:

```yaml
# values/dfe-engine-default-values.yaml
extraEnv:
  DFE_SCHEMAS_OVERLAY_DIR: /var/run/dfe/deploy-repo/config/schemas
```

Lay it out the way dfe-schemas is laid out -- a `manifest.yaml` naming every object, and the
definition files it points at. The engine renders both trees for the topology it
senses and applies them in one pass.

The rules, each enforced at apply rather than written down and hoped for:

- an object whose definition sits under a core directory (`common-header/`,
  `registries/`, `roles/`, `tables/core/`, `tables/internal/`, `tables/meta/`,
  `tables/otel/`, `tables/usage/`, `topics/`, `views/`) is REFUSED by name
- an object whose id the core manifest already declares is REFUSED by name
- a refusal does not stop the core apply: the rest converges and the refusal is
  reported
- the overlay is optional. An install with no deploy repo boots core-only.

Every refusal, and every object the pass applied, is on
`GET /api/v1/system/schema` on the engine, with the reason.

There is no schema pin here. The wheel rides inside the engine image, so the
engine pin selects the schema release -- `GET /api/v1/system/version` reports it
as `schemas`. A deployment that wants a different schema tree uses this overlay,
not a pin.
