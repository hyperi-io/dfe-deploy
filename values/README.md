# values/ -- THE helm-values home (hard standard)

**Every helm value for this environment lives here, one file per service
instance: `{service}-{instance}-values.yaml`. Human and engine edits land in
the SAME files.** There is no second overlay directory - this rule is the
standard, not a convention (dfe-docs `deployment/state-and-repos.md`).

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
env:
  # scalo defaults the OTel service.name to the app name, which leaves two
  # instances of one app indistinguishable in the otel tables.
  OTEL_SERVICE_NAME: dfe-transform-vrl-edge
keda:
  minReplicaCount: 1
  maxReplicaCount: 10
resources:
  requests: {cpu: 100m, memory: 128Mi}
  limits: {cpu: 500m, memory: 512Mi}
```

## The receiver's ingest door

`dfe-receiver` ships `exposure.mode: public`, so a fresh deploy renders a
LoadBalancer per protocol family carrying its `exposed` listeners. The
allow-list is `exposure.public.loadBalancerSourceRanges`, and it ships
EMPTY, which is `0.0.0.0/0` -- the whole internet, not "unset". The
receiver's own `server.auth.mode` defaults to `none`, so an untouched
public deploy accepts unauthenticated posts to `/ingest` from anywhere.

Set one or both in the instance file:

```yaml
exposure:
  public:
    loadBalancerSourceRanges:
      - 203.0.113.0/24
config:
  server:
    auth:
      mode: bearer
```

A deployment with no LoadBalancer provisioner uses `exposure.mode:
internal` instead, which routes ingest through the cluster Gateway on
`receiver.{domain}` (`routes.receiver` in envoy-gateway-config -- enable
both together). That path carries HTTP only, so any other listener left
`exposed: true` fails the chart render rather than deploying a port
nothing reaches.

## Files an app reads off disk

Apps that read their own content files - the transforms - carry it inline
here, as a list of `{name, content}`. The chart renders the list into a
ConfigMap and mounts it. Content lives in the values rather than as loose
files in this repo because Helm cannot read a raw file out of an Argo
`$values` source.

```yaml
transformFiles:
  - name: 000_parse.vrl
    content: |
      . = parse_json!(.message)
      .ts = to_timestamp!(.timestamp)
```

A block scalar keeps the bytes verbatim, so VRL stays exact and a Vector
transform keeps its comments and its own nested `source: |` block. The
ceiling is the ~1 MiB ConfigMap limit; large shipped payloads and binary
enrichment tables belong in an image or object store, not here.
