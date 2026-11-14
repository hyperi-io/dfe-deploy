# Contributing

## Context

Depth, and the reasoning behind the layout: [docs/architecture.md](docs/architecture.md).

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
| `config/` | hot-read config-as-code: `sources/`, `schemas/`, `rules/`, `hunts/`. The engine adds `compat-profiles/` and `library/` on first write |
| `governance/` | five curated dials in `actions/`, protected-var patterns in `policies/` |
| `tools/validate_governance.py` | the structural validator for `governance/` |

Every directory carries its own README. Read `values/README.md` and
`infra/README.md` before a first edit.

### Commands that prove a change

```bash
python3 tools/validate_governance.py
python3 -m unittest discover -s tools
```

The whole local gate: the required fields of each action and policy, closed param constraints, reference wiring
and the guard against an action changing a governance class. How it lies:

- `validate-governance.yaml` filters `paths:` on BOTH `push` and `pull_request`,
  to `governance/**` and `tools/**`. A PR touching only `values/`,
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
| Expect an untouched `dfe-receiver` to take traffic | Name the senders in `exposure.groups.ingest.allow` in `infra/common.yaml` | On the load balancer door an EMPTY allow list renders no load balancer at all, and a `/0` opens it to everyone. The retired `exposure.public.loadBalancerSourceRanges` fails the render |
| Set `env:` or `transformFiles` in an instance file | Use `otel.serviceName` and `fileSets.<set>.files` | `env:` is not a key the thin charts read and renders nothing. `transformFiles` fails the render by name |

### Where this sits

| Repo | Direction | Kind | Mechanism |
|---|---|---|---|
| dfe-infra | inbound | `version-pin` | `pins.yaml` `base.dfe-infra` names one tag whose `versions.yaml` is the manifest for every app image, operator and data service. Pulled by reference, never vendored. `pins.yaml` also calls `dfe-infra/scripts/dfe-stack` by path. Move it, then re-run the validation |
| dfe-schemas | inbound | none | No pin, deliberately, since `e3b2ca9` (2026-09-18). The wheel rides inside the dfe-engine image, so the dfe-infra pin already selects the schema release |
| dfe-infra | outbound | `version-pin` | `versions.yaml` `content.dfe-deploy` pins this repo's tag per stack and bootstrap seeds from it, so a change lands in a deployment only once a stack pins a newer tag |
| dfe-engine | outbound | commits into a copy | Writes a deployment's COPY through gitcrud -- `helmvars` for `values/`, `governance/`, and the config classes. Never the base, never this repo. Not declared in `dfe-infra/suite.yaml` |
