# values/ -- THE helm-values home for APP INSTANCES (hard standard)

**Every helm value for an app instance in this environment lives here, one file
per service instance: `{service}-{instance}-values.yaml`. Human and engine edits
land in the SAME files.** (dfe-infra `docs/deployment/state-and-repos.md`.)

The substrate and platform charts - ClickHouse, Kafka, the network policies, the
gateway - are NOT app instances and do not belong here. They have their own
overlay directory, [`infra/`](../infra/README.md), for the reason in the next
section.

## Nothing but instance files, and nothing in a subdirectory

The ApplicationSet's git files generator globs `values/*-values.yaml`, and Argo
CD passes that to `git ls-files` as a pathspec. A pathspec without `:(glob)`
magic lets `*` match `/`, so `values/anything/foo-values.yaml` MATCHES and
becomes an Argo application too. Proven:

```
$ git ls-files --full-name -- 'values/*-values.yaml'
values/dfe-receiver-default-values.yaml
values/infra/clickhouse-cluster-values.yaml     <- a subdirectory does not hide it
```

So a subdirectory under `values/` is not a safe parking spot for anything. That
is why `infra/` sits at the repo root: the pathspec is anchored on `values/`, so
nothing under `infra/` can ever match it.

How it works:

- The dfe-infra ApplicationSet's git files generator globs
  `values/*-values.yaml` in this repo: **one file = one deployed app
  instance**. Creating `dfe-receiver-default-values.yaml` enables a receiver;
  deleting it removes the app. Do NOT park scratch YAML here - any
  `*-values.yaml` file becomes an Argo application.
- File CONTENT is plain chart values for that service (top-level keys,
  e.g. `image.tag`, `resources`, `keda`), attached to the app as a
  `$values` file over the pinned base + cloud + profile layers. The
  environment's cloud/profile selection comes from cluster annotations,
  not from a values file.
- dfe-engine writes these files by commit (the gitcrud `helmvars` class,
  RBAC `helmvars:write`); operators edit the same files by PR. Git history
  is the audit trail either way.
- Per-component version overrides (`pins.yaml` `overrides:`) are applied by
  merging the emitted fragment into the SERVICE'S EXISTING values file here
  (`dfe-stack resolve --emit-values` prints per-service fragments with the
  target filename) - never as a new standalone file, which would spawn a
  phantom app.

## What an instance file must carry

The `deploy` block is not optional: the ApplicationSet reads it to name the
Argo Application, so a file without it produces nothing at all.

```yaml
deploy:
  service: dfe-transform-vrl
  instance: edge
# An app that runs once per source also needs its own object names, consumer
# group and OTel service.name. Without them two instances of one app collide on
# names and are indistinguishable in the otel tables. A stack-wide app such as
# dfe-receiver carries the deploy block alone.
fullnameOverride: dfe-transform-vrl-edge
component: transform-vrl-edge
otel:
  serviceName: dfe-transform-vrl-edge
config:
  source: {group_id: dfe-transform-vrl-edge, topics: [edge_land]}
  sink: {topic: edge_load}
keda:
  minReplicaCount: 1
  maxReplicaCount: 10
resources:
  requests: {cpu: 100m, memory: 128Mi}
  limits: {cpu: 500m, memory: 512Mi}
```

## The receiver's ingest door

The ingest door is `exposure.groups.ingest`, a deployment-wide setting
read by the receiver and the gateway alike, so it lives in
[`infra/common.yaml`](../infra/README.md), not in the receiver's instance
file. On `door: loadbalancer` (the cloud default) an EMPTY `allow` renders
no load balancer at all, so a fresh deploy has no public ingest until the
senders are named:

```yaml
# infra/common.yaml
exposure:
  groups:
    ingest:
      allow:
        - 203.0.113.0/24
```

A `/0` in `allow` is open to every address. The allow list is not
authentication: a listener no ingest credential lists runs
`server.auth.mode: none`, and the engine switches it to `bearer` once a
credential names it.

A deployment with no LoadBalancer provisioner sets `door: gateway`
instead, which routes ingest through the cluster Gateway on
`receiver.{domain}`. That path carries HTTP only, so any other listener
left `exposed: true` fails the chart render rather than deploying a port
nothing reaches. The retired keys `exposure.mode` and
`exposure.public.loadBalancerSourceRanges` fail the render by name. The
full model is dfe-infra `docs/INGEST-EDGE.md`.

## Files an app reads off disk

Apps that read their own content files - the transforms - carry it inline
here, as a list of `{name, content}` under `fileSets.<set>.files`. The
chart renders the list into a ConfigMap and mounts it. Content lives in
the values rather than as loose files in this repo because Helm cannot
read a raw file out of an Argo `$values` source. The old `transformFiles`
key fails the render.

```yaml
fileSets:
  transforms:
    files:
      - name: 000_parse.vrl
        content: |
          . = parse_json!(.message)
          .ts = to_timestamp!(.timestamp)
```

A block scalar keeps the bytes verbatim, so VRL stays exact and a Vector
transform keeps its comments and its own nested `source: |` block. The
ceiling is the ~1 MiB ConfigMap limit; large shipped payloads and binary
enrichment tables belong in an image or object store, not here.
