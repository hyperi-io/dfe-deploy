# dfe-deploy architecture

A deployment keeps its state in git and reads dfe-infra's charts by reference, and the layout below follows from that split. Each directory's README has the detail for its tree, and [Figure 1](README.md) shows who reads and writes the repo.

A DFE deployment holds two kinds of state that change on different clocks.

HyperI ships one kind: charts, ApplicationSets, images, operators, tier defaults. The deployment creates the other: which apps run and how many, how big each one is, which sources feed it, which rules and hunts analysts wrote, which OIDC providers authenticate people.

Put both in one repository and a base upgrade either overwrites the deployment's choices or has to be hand-merged forever. Copy the base into the deployment's repository and every upgrade is a merge conflict against files nobody in that deployment wrote.

Every operational change has to be auditable as well, and the deployment has to stay manageable when the engine and the UI are both down. That rules out a database as the authority and it rules out the API as the one way in.

## Git holds the deployment's half

Split the two kinds of state, and make git the authority for the second.

- The base is REFERENCED, never copied in and never a submodule. Argo CD renders dfe-infra's charts at the cluster secret's `dfe.hyperi.io/target_revision`, and each app's chart over OCI by a digest that revision's ApplicationSet pins.
- `pins.yaml` records which stack that revision is. `dfe-ops upgrade apply --push` bumps `base.dfe-infra`, pushes it and moves `target_revision` in step, and dfe-engine reports the stack on `GET /api/v1/system/version`. A hand edit of the pin alone leaves the charts where they were.
- The deployment's state is OWNED outright, in a read-write repository per environment.
- Every mutation is a commit, whoever makes it. dfe-engine commits, operators commit by pull request, and the git history is the audit trail either way. Editing the files directly still works, which keeps a deployment manageable with the control plane down.

This repository is the seed for the second half. A copy is made three ways: dfe-infra's bootstrap creates a bundled Forgejo repo, a forge copies the template, or someone clones at a release tag and re-homes the remote. The bundled repo is not seeded from this template yet ([dfe-infra#13](https://github.com/hyperi-io/dfe-infra/issues/13)). Never fork: a fork of a public repo cannot be private, and fork lineage invites merging template history, which the pin model exists to avoid.

## Why `values/` and `infra/` are separate trees

The dfe-infra ApplicationSet's git files generator globs `values/*-values.yaml`, and Argo passes that glob to `git ls-files` as a pathspec. A pathspec without `:(glob)` magic lets `*` match `/`. So `values/infra/kafka-values.yaml` matches the glob and becomes an Argo application.

That single fact drives the layout. `values/` holds app instances and nothing else, not even in a subdirectory, because a subdirectory does not hide a file from the generator. `infra/` therefore sits at the repository root, where a pathspec anchored on `values/` cannot reach it, and takes the values for everything that is not an app instance: ClickHouse, Kafka, DocumentDB, the OTel collector, the network policies, the gateway config.

## The values cascade

Helm applies `-f` files in order and the last wins. Each ApplicationSet stacks dfe-infra's defaults first and this repo's files last:

| Layer | Repo | Read by |
|---|---|---|
| `argocd/values/common.yaml` | dfe-infra | every appset below |
| `argocd/values/<cloud>.yaml` | dfe-infra | every appset below |
| `argocd/values/profile-<profile>.yaml` | dfe-infra | every appset below |
| `argocd/values/apps/...` | dfe-infra | apps and the edge tunnel: `_common.yaml`, then the app's `values.yaml`, `<cloud>.yaml` and `profile-<profile>.yaml` |
| `sizing/<profile>.data-charts.values.yaml`, `sizing/<app>.values.yaml` | here | data and platform |
| `infra/common.yaml` | here | apps, data, platform and edge |
| `infra/<app>.yaml` | here | data, platform and the edge gateway |
| `values/<svc>-<inst>-values.yaml` | here | apps, and the edge tunnel for `values/culvert-*-values.yaml` |

Both edge ApplicationSets add `argocd/values/edge-<flavour>.yaml` after the cloud file. Facts the cluster secret holds, such as the domain and the registry, arrive as Helm parameters and beat every file.

A profile file is a tier DEFAULT, not a lock, so a deployment can declare `clickhouse.mode: external` in `infra/common.yaml` and beat `profile-scale.yaml`. A fact more than one chart consumes belongs in `infra/common.yaml` once, so the network policy, the ClickHouse chart and the loader cannot disagree about it.

## Governed ops

`governance/` is the content behind the engine's governed-operations API, and it is built so that a curated dial cannot become a general-purpose write.

- An action is a bundle of var changes, invoked by name and applied atomically in one commit. An operator granted `action:invoke:<name>` can pull that one lever without holding raw `helmvars:write`, and every invoke supports a dry run that returns the diff and commits nothing.
- Params are closed by construction. An enum lists every value, a numeric has both bounds, and there is no free-string param type. Values substitute whole-value, never into `cls`, `name` or `path`.
- An action may never change a governance class. That is a privilege-escalation guard, enforced at both validate and invoke, and independently by `tools/validate_governance.py`.
- A policy is a list of `cls:name:path` fnmatch patterns that locks matching vars against Tier-1 edits and against actions, unless the caller holds `helmvars:override`. The shipped `baseline` policy locks `image.*`, because image references move through stack pins rather than dials.

A policy governs the API, not the repository. A direct git commit still lands, which is deliberate: git is the authority and the API is a window over it.

## Invariants

These are the ones reading the files will not tell you.

1. Any `values/*-values.yaml` file IS an application. Creating one enables the app, deleting one removes it, and a scratch file spawns a phantom app.
2. An instance file without a `deploy:` block produces no application. The ApplicationSet names the Argo Application from `deploy.service` and `deploy.instance` and renders with `missingkey=error`, so a missing key is a render error and no Application appears.
3. `config/schemas/` is ADDITIVE. An object whose definition sits under a core directory, or whose id the core manifest declares, is rejected by name. A rejection does not stop the core apply: the rest converges and the rejection is reported on `GET /api/v1/system/schema`.
4. There is no DDL Job. dfe-engine applies every ClickHouse object and every bootstrap Kafka topic at its startup, from the `dfe-schemas` wheel inside its image. That is why there is no `dfe-schemas` pin.
5. The data-store mode and storage model are chosen at deploy and rejected by the engine's API afterwards, and node and broker counts can rise but not fall. Changing either on a live deployment is a data migration, not a values edit.
6. Object-store credentials never appear in these files. Both data charts read them from the environment, wired from a Secret the secrets store materialises.
7. Validation here is structural. A chart renaming a dial var is caught by dfe-infra's chart validation, which owns the charts these paths point into.
8. Zero governance files is a FAILURE, not a pass. An empty result means the tree moved or the path is wrong, and a validator reporting success having checked nothing is the fault it exists to catch.

Some state is deliberately not here. Per-user UI state (saved searches, dashboards, preferences) lives in the app databases, dfe-hyperdx's in DocumentDB, never in git. Secrets live in the secrets store. Nothing in `config/` is a Kubernetes manifest, and Argo never applies it as one: dfe-engine reads the tree from its clone, and its hunt runner reads `hunts/` and `rules/` from a git-sync volume.
