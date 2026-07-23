# governance/ -- curated actions + protected-var policies

The Governed Ops content for this deployment. dfe-engine reads and commits
this tree (RBAC class `governance`); operators and admins can equally edit it
by PR. If the engine and UI are both down, DFE stays fully manageable by
editing these files directly - git is the authority.

## actions/ -- the shipped operational dials

Each file is one curated action: a named, RBAC-gated bundle of var changes
applied atomically in ONE commit via
`POST /api/v1/governance/actions/{name}/invoke` (or `dfe-api`). Operators are
granted per-dial `action:invoke:<name>` handles - they can pull a lever
without holding raw `helmvars:write`. Every invoke supports
`?dry_run=true` (returns the diff, commits nothing).

Shipped dials:

| action | what it does | params |
|---|---|---|
| `receiver-surge` | raise the receiver KEDA ceiling for an ingest surge | `level`: 2x / 4x |
| `receiver-normal` | restore the baseline ceiling | - |
| `hunts-pause` | stop the hunt runner (shed ClickHouse load) | - |
| `hunts-resume` | restart the hunt runner (resumes from checkpoints) | - |
| `hunts-throttle` | cap concurrent hunt runs | `cap`: 1-32 |

Params are CONSTRAINED by design - an enum carries its full value list, a
numeric carries both bounds. There is no free-string param type. Values
substitute whole-value only (`{$param: name}` or a per-value `map`), never
into `cls`/`name`/`path`.

The `changes[].name` entries reference the per-instance values files in
`../values/` (`{service}-{instance}-values` - see `values/README.md`). If an
instance file does not exist yet, an invoke creates it - and any
`*-values.yaml` file IS an Argo application, so point actions only at
instances this deployment actually runs.

Authoring a new action: validate first with
`POST /api/v1/governance/admin/actions/validate` (returns every violation and
the would-be diff without committing), then define via
`POST /api/v1/governance/admin/actions` (`governance:write`). Actions may
never change the `governance` class itself - that is a privilege-escalation
guard, enforced at both validate and invoke.

## policies/ -- protected-var policies

`cls:name:path` fnmatch patterns that lock vars against Tier-1 edits AND
actions unless the caller holds `helmvars:override`. The shipped `baseline`
policy locks `image.*` - image references move through stack pins
(`dfe-stack resolve`), not dials.

## Validation

`tools/validate_governance.py` structurally validates this tree (schema
shape, closed param constraints, reference wiring, no governance-class
changes) and runs in CI on every PR. Chart-path drift (a chart renaming a
dial var) is covered by dfe-infra's chart validation, which owns the charts
these paths point into.
