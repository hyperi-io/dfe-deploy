# Contributing

## Context

Depth, and the reasoning behind the layout: [docs/architecture.md](docs/architecture.md).

### What this is

The template a deployment's git repo is copied FROM -- never itself a live deploy repo, so nothing here is reconciled to a cluster. A deployment takes a read-write copy, and Argo CD, dfe-engine and operators read and write that. Not the base either: charts and ApplicationSets live in dfe-infra, which Argo CD renders at the cluster secret's `target_revision`. The code is in `tools/`, two scripts and their tests, and there is no Kubernetes manifest.

### Where things live

| Path | Holds |
|---|---|
| `pins.yaml` | the dfe-infra stack the deployment runs, the release `channel`, per-component `overrides` |
| `values/` | one `{service}-{instance}-values.yaml` per APP instance -- file presence enables the app |
| `infra/` | `common.yaml` plus one `<app>.yaml` per data, platform or edge chart |
| `config/` | config-as-code dfe-engine reads: `sources/`, `schemas/`, `rules/`, `hunts/`. The engine adds `compat-profiles/` and `library/` on first write |
| `governance/` | curated dials in `actions/`, protected-var patterns in `policies/`, byte-identical to the copies dfe-engine seeds |
| `sizing/` | the sizing resolver's committed output, none in the template |
| `tools/validate_governance.py` | the structural validator for `governance/` |
| `tools/changelog_backfill.py` | adds a `CHANGELOG.md` entry for any release tag the file misses, run by `release.yaml` |

Every directory has a README. Read `values/README.md` and `infra/README.md` before a first edit.

### Commands that prove a change

```bash
python3 tools/validate_governance.py
python3 -m unittest discover -s tools
```

The whole local gate: the required fields of each action and policy, closed param constraints, declared param references, known resource classes, pinned image refs, and the guard against an action changing a governance class. How it lies:

- `validate-governance.yaml` filters `paths:` on BOTH `push` and `pull_request`, to `governance/**` and `tools/**`. A PR touching nothing but `values/`, `config/`, `pins.yaml` or a README shows CodeQL alone: the governance gate did not run, which is not a pass.
- `release.yaml` has no path filter and re-runs the gate before tagging, so a
  docs change is checked on merge rather than in review. semantic-release exits 0
  either way, so it reads `git tag --points-at HEAD` instead.
- Nothing validates `values/`, `infra/` or `config/`. Chart-var drift belongs to
  dfe-infra's chart validation, and a typo in an instance file surfaces in Argo.

### What tends to bite

| Don't | Do | Why |
|---|---|---|
| Park YAML under `values/`, subdirectories included | Put anything that is not an app instance in `infra/` | Argo hands the `values/*-values.yaml` glob to `git ls-files` as a pathspec, where `*` matches `/` -- so a subdirectory file becomes a phantom Argo app (`99289a4`, `976a898`) |
| Fork this repo | Use the template, or clone at the tag and re-home | A fork of a public repo cannot be private, and base updates arrive through `pins.yaml` and `dfe-ops upgrade`, never by merging template history (`9b800f1`) |
| Omit `deploy:` from an instance file | Name `deploy.service` and `deploy.instance` | The ApplicationSet reads it to name the Application and renders with `missingkey=error`, so the file yields no app (`1874994`) |
| Expect a Job to apply `config/schemas/` | Treat it as the engine's additive overlay | There is no Job -- the engine applies every object at its startup (`e3b2ca9`) |
| Expect an untouched `dfe-receiver` on a cloud to take traffic | Name the senders in `exposure.groups.ingest.allow` in `infra/common.yaml` | On the load balancer door, the cloud default, an EMPTY allow list renders no load balancer at all, and a `/0` opens it to everyone. The retired `exposure.public.loadBalancerSourceRanges` fails the render |
| Set `env:` or `transformFiles` in an instance file | Use `extraEnv`, `otel.serviceName` and `fileSets.<set>.files` | `env` is the environment name the ApplicationSet sets as a parameter, so a variable map there renders nothing. `transformFiles` fails the render by name |

### Where this sits

| Repo | Direction | Kind | Mechanism |
|---|---|---|---|
| dfe-infra | inbound | `version-pin` | `pins.yaml` `base.dfe-infra` names the stack. Its `versions.yaml` lists every app image, operator and data service. `dfe-ops upgrade` and `dfe-stack resolve` read it, and Argo CD renders from the cluster secret's `target_revision`. The `pins.yaml` usage comment calls `dfe-infra/scripts/dfe-stack` by path: move the script, then update the comment |
| dfe-schemas | inbound | none | No pin, deliberately, since `e3b2ca9` (2026-09-18). The wheel rides inside the dfe-engine image, so the dfe-infra pin selects the schema release |
| dfe-infra | outbound | `version-pin` | `versions.yaml` `content.dfe-deploy` pins this repo's tag per stack, and `dfe-stack release-gate` fails a stack when the pinned template's `pins.yaml` names another stack. Bootstrap does not seed from it yet ([dfe-infra#13](https://github.com/hyperi-io/dfe-infra/issues/13)) |
| dfe-engine | outbound | commits into a copy | Writes a deployment's COPY through gitcrud -- `helmvars` for `values/`, `infravars` for `infra/`, the governance classes and the config classes -- and seeds any shipped action or policy file the copy lacks. Never the base, never this repo. Not declared in `dfe-infra/suite.yaml` |
