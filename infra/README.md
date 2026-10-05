# infra/ -- the deployer's overlay for everything that is not an app instance

`values/` holds one file per APP instance and each of those files becomes an Argo
application. The substrate and platform charts are not app instances - ClickHouse,
Kafka, PostgreSQL, FerretDB, the OTel collector, the network policies, the gateway
config. dfe-infra decides they exist; this directory is where a deployment says
what shape they take.

Two kinds of file, both optional:

- **`common.yaml`** - deployment-wide facts, read by EVERY appset (platform, data
  and apps). This is the deployer's own `argocd/values/common.yaml`. A fact more
  than one chart consumes - `clickhouse.mode`, `kafka.mode` - is declared here
  once, so the network policy, the ClickHouse chart and the loader cannot
  disagree about it.
- **`<chart>.yaml`** - one chart's own values, read by the platform and data
  appsets only. The name is the dfe-infra chart directory:
  `clickhouse-cluster.yaml`, `kafka.yaml`, `ferretdb.yaml`,
  `otel-collector.yaml`, `dfe-schema.yaml`, `kafbat.yaml`, `links.yaml`,
  `network-policies.yaml`, `envoy-gateway-config.yaml`.

Content is plain chart values, same as `values/`. There is no `deploy:` block
here - nothing in this directory creates an application.

## Why not a subdirectory of values/

Because a subdirectory of `values/` is not hidden from the app generator. Argo
passes the `values/*-values.yaml` glob to `git ls-files` as a pathspec, and a
pathspec without `:(glob)` magic lets `*` match `/`. `values/infra/kafka-values.yaml`
matches, and a phantom application appears. `infra/` at the repo root cannot
match a pathspec anchored on `values/`. See [`values/README.md`](../values/README.md).

## Where these files land in the cascade

Helm applies `-f` files in order and the last one wins. The appsets stack them:

```
argocd/values/common.yaml            dfe-infra   the product SSoT
argocd/values/<cloud>.yaml           dfe-infra   cloud specifics
argocd/values/profile-<profile>.yaml dfe-infra   the TIER default
infra/common.yaml                    HERE        deployment-wide
infra/<chart>.yaml                   HERE        this chart          (platform + data)
values/<svc>-<inst>-values.yaml      values/     this instance       (apps)
```

The profile file is a tier DEFAULT, not a lock. `profile-scale.yaml` declares
`clickhouse.mode: cluster`; declaring `clickhouse.mode: external` in
`infra/common.yaml` beats it, and the derived external-service egress opens with
it. Before this layer existed a deployer had to edit dfe-infra to get there.

Moving a mode means moving its endpoint in the same file - `clickhouse.host` for
ClickHouse, `kafka.bootstrapServers` for Kafka - because the profile pins those
to the in-cluster service names.

## The storage model, and the keys the engine refuses to change

Both data stores take a storage model that is chosen at deploy and refused
afterwards. Models are named `<family>-<bulk>`: the family says whether data
MOVES to the bulk store or is COPIED to it, the bulk half says what that store
is. `local` is the default on both and changes nothing.

```yaml
# infra/clickhouse-cluster.yaml
clickhouse:
  storageModel: cached-object     # or tiered-block, or local (default)
  objectStore:
    endpoint: https://my-bucket.s3.ap-southeast-2.amazonaws.com/clickhouse/
    cacheSize: 20Gi
```

```yaml
# infra/kafka.yaml
kafka:
  storageModel: tiered-object     # or local (default)
  tieredObject:
    className: io.aiven.kafka.tieredstorage.RemoteStorageManager
    classPath: /opt/kafka/plugins/tiered-storage/*
    config:
      storage.backend.class: io.aiven.kafka.tieredstorage.storage.s3.S3Storage
      storage.s3.bucket.name: my-kafka-bucket
```

`cached-object` puts ClickHouse parts on an object-store disk behind a local
read-through cache, so the PVC stops being the capacity ceiling and the cache
stays disposable. `tiered-block` ranks a hot SSD volume over a cold bulk volume
and demotes the oldest parts as the hot one fills, needing no object store -
data MOVES, so both volumes must be durable. `tiered-object` moves closed Kafka
segments to object storage (KIP-405 tiered storage), so the PVC sizes the hot
window; Strimzi ships no RemoteStorageManager, so it needs a broker image
carrying a plugin, and the chart fails the render rather than deploying a broker
that looks configured and tiers nothing.

Every combination, whether it ships and how well proven it is: dfe-infra
`docs/deployment/storage.md`.

Object-store CREDENTIALS never appear in these files. Both charts read them from
the environment, wired from a Secret the secrets store materialises - seed
`<project>/<env>/clickhouse/s3` and `<project>/<env>/kafka/tiered` with
`access_key_id` and `secret_access_key`. A credential that already lives at a
different path or under different field names binds without reseeding:
`clickhouse.objectStore.remoteKey` / `kafka.objectStore.remoteKey` name the path,
`accessKeyProperty` / `secretKeyProperty` name the fields, and
`secretStoreName` selects the store that mounts them.

The engine holds these as protected vars and refuses a post-deploy edit with the
policy that blocked it (`governance/policies/storage-layout.yaml`):

| key | why it locks |
|---|---|
| `clickhouse.mode`, `kafka.mode` | where the data lives; moving it strands every existing row |
| `clickhouse.storageModel`, `kafka.storageModel` | the on-disk layout, chosen once |
| `clickhouse.objectStore.*`, `kafka.objectStore.*` | the object-store location the existing parts and segments are in |
| `clickhouse.tieredBlock.*`, `kafka.tieredObject.*` | the cold volume holding the only copy of what it carries, and the plugin that reaches the bucket |
| `clickhouse.storage.size`, `.storageClass` and the kafka pair | `volumeClaimTemplates` are immutable, so no sync applies it |

A deployment created before this vocabulary keeps its `storage-model.yaml`
alongside the new file - the engine never rewrites a policy it already seeded -
and the shipped lock carries the older key spellings so nothing goes unprotected
while a deployment is still on an older chart.

A holder of `helmvars:override` can still make a deliberate exception, and a
direct git commit still gets through - the policy governs the API, not the repo.
Changing any of these on a live deployment is a data migration, not a values edit.

## Node and broker counts go up, never down

`clickhouse.replicas`, `clickhouse.keeper.replicas` and `kafka.replicas` are
accepted upward and refused downward, and not out of caution. Removing a
ClickHouse node drops a copy of the data, or the data itself when the cluster is
sharded; a Kafka broker takes every partition replica it held unless those are
reassigned first; a Keeper ensemble can lose its Raft quorum, which takes every
replicated table read-only with it. Do the move, then lower the count.

The refusal compares what the overlay stack DECLARES before and after, so nothing
declared means nothing to compare and the write is accepted. CPU and memory move
freely in both directions.

## Storage size is not the answer

Growing a PVC needs `allowVolumeExpansion: true` on the StorageClass and, because
`volumeClaimTemplates` are immutable, a StatefulSet recreate. `local-path` has no
resize support at all. That is what the storage model exists to avoid, so reach
for a non-`local` model before reaching for a bigger disk. The size and class
keys are protected for the same reason.

dfe-docker is the other way round: `DFE_DATA_ROOT` picks WHICH disk, and a bind
mount takes whatever that disk has. k8s locks size and class; docker locks
location.
