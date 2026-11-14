# dfe-deploy

The template a DFE deployment's own git repo is seeded from.

[![License](https://img.shields.io/badge/license-BUSL--1.1-blue)](LICENSE)

## What it does

- Each deployment takes its own read-write copy of this repo. That copy holds everything local to the deployment, and the base, dfe-infra, is pulled by reference at the tag `pins.yaml` names, never vendored in.
- `pins.yaml`: one dfe-infra tag selects the certified stack as the baseline, with the release channel and any per-component overrides beside it. Updating the base is a one-line bump that leaves your files alone.
- `values/`: one Helm values file per app instance. A file named for the instance and carrying its `deploy` block is what turns the app on.
- `infra/`: an optional `common.yaml` plus one optional values file per data or platform chart.
- `config/`: sources, detection rules and hunts as config-as-code, read hot by the DFE apps and dfe-engine, and `config/schemas/`, the additive schema overlay dfe-engine applies at startup.
- `governance/`: the dials and protected-variable policies, checked by `tools/validate_governance.py`.

dfe-engine writes only this copy, by commit, so the audit trail is its git history. It never writes the base.

## Quick start

Take a copy, never a fork. A fork of a public repo cannot be private, and base updates arrive by bumping `pins.yaml`, never by merging template history. Three ways, in order of preference:

1. Let dfe-infra's bootstrap seed the deploy repo in the bundled in-cluster Forgejo from this template at the stack's tag. This is the default and works air-gapped.
2. GitHub "Use this template" or GitLab "new from template", for a fresh private repo with no upstream lineage.
3. Clone at the release tag, remove `origin`, push to your own remote.

Then check the governance files before the first commit:

```bash
python3 tools/validate_governance.py
```

## Configuration

Bump the dfe-infra version in `pins.yaml` to update the base. Your `values/` and `config/` are untouched, and the schema release moves with the dfe-engine image that stack pins, because the dfe-schemas wheel rides inside it. Who writes what: `pins.yaml` is yours, `values/` is yours and dfe-engine's in the same files, `config/` is dfe-engine's and your analysts'. Per-user console state (saved searches, dashboards) is not here. It lives in the app databases.

## Documentation

- [docs/architecture.md](docs/architecture.md): how a deployment repo is laid out, and why.
- [values/README.md](values/README.md), [infra/README.md](infra/README.md) and [config/README.md](config/README.md): each directory's own rules, to read before a first edit.
- dfe-infra [docs/deployment/state-and-repos.md](https://github.com/hyperi-io/dfe-infra/blob/main/docs/deployment/state-and-repos.md) and [docs/deployment/stack-versioning.md](https://github.com/hyperi-io/dfe-infra/blob/main/docs/deployment/stack-versioning.md): the canonical model and the diagrams.

The suite's published docs are at <https://dfe.docs.hyperi.io>, and this repository's pages at <https://dfe.docs.hyperi.io/dfe-deploy/>.

## Help and contributing

How to work in this repo, the commands that prove a change and what tends to bite are in [CONTRIBUTING.md](CONTRIBUTING.md). A question that is not a bug goes in a new issue.

Open bugs: [this repo](https://github.com/hyperi-io/dfe-deploy/issues?q=is%3Aopen+is%3Aissue+type%3ABug+-label%3Abacklog+-label%3Anext-minor) | [whole DFE suite](https://github.com/search?type=issues&q=is%3Aopen+is%3Aissue+type%3ABug+-label%3Abacklog+-label%3Anext-minor+repo%3Ahyperi-io%2Fdfe-infra+repo%3Ahyperi-io%2Fdfe-docker+repo%3Ahyperi-io%2Fdfe-deploy+repo%3Ahyperi-io%2Fdfe-engine+repo%3Ahyperi-io%2Fdfe-loader+repo%3Ahyperi-io%2Fdfe-receiver+repo%3Ahyperi-io%2Fdfe-fetcher+repo%3Ahyperi-io%2Fdfe-archiver+repo%3Ahyperi-io%2Fdfe-transform-vrl+repo%3Ahyperi-io%2Fdfe-transform-vector+repo%3Ahyperi-io%2Fdfe-transform-elastic+repo%3Ahyperi-io%2Fdfe-ui+repo%3Ahyperi-io%2Fdfe-hyperdx+repo%3Ahyperi-io%2Fscalo-rs+repo%3Ahyperi-io%2Fscalo-py+repo%3Ahyperi-io%2Flogreducer+repo%3Ahyperi-io%2Fdfe-schemas+repo%3Ahyperi-io%2Fvector-vrl+repo%3Ahyperi-io%2Fculvert+repo%3Ahyperi-io%2Fdfe-clickhouse-rs+repo%3Ahyperi-io%2Ffactbook-rs)

## License

BUSL-1.1, see [LICENSE](LICENSE). (c) 2026 HYPERI PTY LIMITED
