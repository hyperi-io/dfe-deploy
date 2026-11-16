# dfe-deploy

The template a DFE deployment's own git repo is seeded from.

[![License](https://img.shields.io/badge/license-BUSL--1.1-blue)](LICENSE)

## What it does

- Each deployment takes a read-write copy of this repo, which holds everything local to the deployment. The base, dfe-infra, stays in its repo and Argo CD reads it by reference.
- `pins.yaml`: the dfe-infra stack the deployment runs, with the release channel and any per-component overrides beside it.
- `values/`: one Helm values file per app instance. A file named for the instance, with its `deploy` block, is what turns the app on.
- `infra/`: an optional `common.yaml` plus one optional values file per data or platform chart.
- `config/`: sources, detection rules and hunts as config-as-code, read by dfe-engine, and `config/schemas/`, the additive schema overlay dfe-engine applies at startup.
- `governance/`: the dials and protected-variable policies, checked by `tools/validate_governance.py`.
- `sizing/`: the sizing resolver's committed output.

dfe-engine writes to this copy by commit, so the audit trail is its git history. It never writes the base.

## Quick start

Take a copy, never a fork. A fork of a public repo cannot be private, and base updates arrive through `pins.yaml`, never by merging template history. Three ways:

1. GitHub "Use this template" or GitLab "new from template", for a fresh private repo with no upstream lineage.
2. Clone at the release tag, remove `origin`, push to your remote.
3. Leave the deploy repo unset and dfe-infra's bootstrap creates one in the bundled in-cluster Forgejo. That repo holds `sizing/` and a values file per app, not this template's files ([dfe-infra#13](https://github.com/hyperi-io/dfe-infra/issues/13)).

Then check the governance files before the first commit:

```bash
python3 tools/validate_governance.py
```

It prints `OK:` with the action and policy counts, and exits 1 on any error or on an empty `governance/`.

## Configuration

`dfe-ops upgrade apply --deploy <your copy> --push` moves a deployment to a newer stack along a path `dfe-stack check-upgrade` reports as `SUPPORTED`. It bumps `base.dfe-infra` in `pins.yaml`, pushes the commit and moves the cluster secret's `target_revision` with it. Without `--push` it rejects a move that needs the retarget, and a hand edit of the pin alone moves no chart. Between two releases there is no verified path, so a release is a fresh deploy (dfe-infra [docs/deployment/upgrades.md](https://github.com/hyperi-io/dfe-infra/blob/main/docs/deployment/upgrades.md)).

The schema release moves with the dfe-engine image the stack pins, because the dfe-schemas wheel rides inside it, so `pins.yaml` has no dfe-schemas pin.

`channel` records the maturity the deployment tracks (`alpha`, `beta`, `rc` or `release`), and no tool selects anything by it. `overrides` moves one app off the certified set, by `tag@sha256` and nothing looser, and dfe-engine logs a SUPPORT-DRIFT notice at startup for each entry:

```yaml
overrides:
  apps:
    dfe-receiver: "v1.16.0@sha256:..."
```

`dfe-stack resolve --pins pins.yaml --emit-values -` prints the values fragment to merge into that service's existing instance file, never a separate file.

Who writes what: `pins.yaml` is yours, `values/` and `infra/` are yours and dfe-engine's in the same files, `config/` is dfe-engine's and your analysts', and `governance/` is dfe-engine's and your admins'. Per-user console state (saved searches, dashboards) is not here. It lives in the app databases.

## Documentation

- [docs/architecture.md](docs/architecture.md): how a deployment repo is laid out, and why.
- [values/README.md](values/README.md), [infra/README.md](infra/README.md), [config/README.md](config/README.md), [governance/README.md](governance/README.md) and [sizing/README.md](sizing/README.md): each directory's rules, to read before a first edit.
- dfe-infra [docs/deployment/state-and-repos.md](https://github.com/hyperi-io/dfe-infra/blob/main/docs/deployment/state-and-repos.md) and [docs/deployment/stack-versioning.md](https://github.com/hyperi-io/dfe-infra/blob/main/docs/deployment/stack-versioning.md): the canonical model and the diagrams.

The suite's published docs are at <https://dfe.docs.hyperi.io>, and this repository's pages at <https://dfe.docs.hyperi.io/dfe-deploy/>.

## Help and contributing

How to work in this repo, the commands that prove a change and what tends to bite are in [CONTRIBUTING.md](CONTRIBUTING.md). A question that is not a bug goes in an issue.

Open bugs: [this repo](https://github.com/hyperi-io/dfe-deploy/issues?q=is%3Aopen+is%3Aissue+type%3ABug+-label%3Abacklog+-label%3Anext-minor) | [whole DFE suite](https://github.com/search?type=issues&q=is%3Aopen+is%3Aissue+type%3ABug+-label%3Abacklog+-label%3Anext-minor+repo%3Ahyperi-io%2Fdfe-infra+repo%3Ahyperi-io%2Fdfe-docker+repo%3Ahyperi-io%2Fdfe-deploy+repo%3Ahyperi-io%2Fdfe-engine+repo%3Ahyperi-io%2Fdfe-loader+repo%3Ahyperi-io%2Fdfe-receiver+repo%3Ahyperi-io%2Fdfe-fetcher+repo%3Ahyperi-io%2Fdfe-archiver+repo%3Ahyperi-io%2Fdfe-transform-vrl+repo%3Ahyperi-io%2Fdfe-transform-vector+repo%3Ahyperi-io%2Fdfe-transform-elastic+repo%3Ahyperi-io%2Fdfe-ui+repo%3Ahyperi-io%2Fdfe-hyperdx+repo%3Ahyperi-io%2Fscalo-rs+repo%3Ahyperi-io%2Fscalo-py+repo%3Ahyperi-io%2Flogreducer+repo%3Ahyperi-io%2Fdfe-schemas+repo%3Ahyperi-io%2Fvector-vrl+repo%3Ahyperi-io%2Fculvert+repo%3Ahyperi-io%2Fdfe-clickhouse-rs+repo%3Ahyperi-io%2Ffactbook-rs)

## License

BUSL-1.1, see [LICENSE](LICENSE). (c) 2026 HYPERI PTY LIMITED
