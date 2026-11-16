# governance/ -- curated actions + protected-var policies

The Governed Ops content for this deployment. dfe-engine reads and commits this tree (RBAC class `governance`), and operators and admins can edit it by PR. If the engine and UI are both down, DFE stays manageable by editing these files directly: git is the authority.

The files here are byte-identical to the library dfe-engine ships. On start the engine commits any shipped action or policy file the repo lacks and leaves every existing file alone, edited or not. A deleted file comes back on the next start unless its name is a line in `governance/.seed-ignore`.

## actions/ -- the shipped operational dials

Each file is one curated action: an RBAC-gated bundle of var changes, invoked by name and applied atomically in ONE commit via `POST /api/v1/governance/actions/{name}/invoke`. Operators are granted per-dial `action:invoke:<name>` handles, so they can pull a lever without holding raw `helmvars:write`. Every invoke supports `?dry_run=true`, which returns the diff and commits nothing.

Shipped dials:

| action | what it does | params |
|---|---|---|
| `receiver-surge` | raise the receiver KEDA ceiling for an ingest surge | `level`: 2x / 4x |
| `receiver-normal` | return to the tier's ceiling by removing the override | - |
| `hunts-pause` | stop the hunt runner (shed ClickHouse load) | - |
| `hunts-resume` | restart the hunt runner (resumes from checkpoints) | - |
| `hunts-throttle` | cap concurrent hunt runs | `cap`: 1-32 |

Params are CONSTRAINED by design: an enum lists every value it takes, and a numeric has both bounds. There is no free-string param type. A param substitutes a whole value (`{$param: name}` or a per-value `map`), never into `cls`, `name` or `path`.

A value of `{$unset: true}` removes the key instead of setting it, so the var returns to the layer beneath the overlay. `receiver-normal` uses it to hand the KEDA ceiling back to the tier profile.

The `changes[].name` entries reference the per-instance values files in `../values/` (`{service}-{instance}-values`, see `values/README.md`). Every shipped action names the `default` instance. If that instance file does not exist, an invoke creates it with its `deploy:` block, which deploys that instance, after the multiplicity and ceiling checks the instance API applies. Point actions at instances this deployment runs.

An action that switches a component off switches off the engine's secret group for it as well (`secrets.<group>.enabled`, as `hunts-pause` does), and its counterpart switches both back on. The component's Secret exists while the component is on, and the engine pod waits on any Secret it reads.

To author an action, validate first with `POST /api/v1/governance/admin/actions/validate`, which returns every violation and the would-be diff without committing, then define it with `POST /api/v1/governance/admin/actions` (`governance:write`). Actions may never change a governance class. That is a privilege-escalation guard, enforced at both validate and invoke.

## policies/ -- protected-var policies

`cls:name:path` fnmatch patterns that lock vars against Tier-1 edits AND actions unless the caller holds `helmvars:override`. The shipped `baseline` policy locks `image.*`, because image references move through stack pins (`dfe-stack resolve`), not dials. `storage-layout` and `sizing-locks` hold the keys chosen at deploy, described in [infra/README.md](../infra/README.md) and [sizing/README.md](../sizing/README.md).

`tools/validate_governance.py` checks this tree's structure: required fields, closed param constraints, declared param references, known resource classes, pinned image refs, and no governance-class changes. CI runs it on a PR or push that touches `governance/` or `tools/`, and the release workflow runs it before every tag. Chart-path drift (a chart renaming a dial var) is covered by dfe-infra's chart validation, which owns the charts these paths point into.
