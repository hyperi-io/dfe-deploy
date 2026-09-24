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
| `schemas/` | this deployment's own schema overlay -- see below | humans + dfe-engine (generated DDL) |
| `transforms/` | VRL, Vector.dev YAML, WASM transform configs | humans + dfe-engine |
| `rules/` | detection rules | analysts + dfe-engine |
| `hunts/` | hunts | analysts + dfe-engine |
| `alerts/` | alert definitions | analysts + dfe-engine |
| `oidc/` | OIDC providers, RBAC assignments | dfe-engine |

NOT here: per-user saved searches / dashboards / preferences -- those are user
state in the app databases (HyperDX FerretDB), never git.

## `schemas/` -- the deployment's own overlay

The core schema is the `dfe-schemas` wheel pinned inside the dfe-engine image,
read-only. This directory is the second tree, and it is **additive**: it may
declare objects the core does not, and it may never redefine one the core does.

Point the engine at it with `DFE_SCHEMAS_OVERLAY_DIR`, and lay it out the way
dfe-schemas is laid out -- a `manifest.yaml` naming every object, and the
definition files it points at. The engine renders both trees for the topology it
senses and applies them in one pass.

The rules, each enforced at apply rather than written down and hoped for:

- an object whose definition sits under a core directory (`common-header/`,
  `registries/`, `roles/`, `tables/core/`, `tables/internal/`, `tables/meta/`,
  `tables/otel/`, `topics/`, `views/`) is REFUSED by name
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
