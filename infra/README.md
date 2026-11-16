# infra/ -- the deployer's overlay for everything that is not an app instance

`values/` holds one file per APP instance, and each of those files becomes an Argo application. The data and platform charts are not app instances: ClickHouse, Kafka, DocumentDB, the OTel collector, Kafbat, the links page, the network policies, the gateway config. dfe-infra decides they exist, and this directory is where a deployment configures them. dfe-engine writes here as the `infravars` class.

Two kinds of file, both optional:

- `common.yaml`: deployment-wide facts, read by the app, data, platform and edge ApplicationSets. A fact more than one chart consumes, such as `clickhouse.mode` or `kafka.mode`, is declared here once, so the network policy, the ClickHouse chart and the loader cannot disagree about it.
- `<app>.yaml`: one chart's values, read by the data, platform and edge ApplicationSets. The name is the ApplicationSet element's `app`, or its `overlay` where one is set, never the chart directory: `clickhouse-cluster.yaml`, `kafka.yaml`, `documentdb.yaml`, `otel-collector.yaml`, `kafbat.yaml`, `links.yaml`, `network-policies.yaml`, `dfe-toolbox.yaml`, `envoy-gateway-config.yaml`, and on AWS `node-pools.yaml`, which the `karpenter-pools` Application reads.

Content is plain chart values, the same as `values/`. There is no `deploy:` block here, and nothing in this directory creates an application. It sits at the repo root rather than under `values/` because the app generator's pathspec reaches into every subdirectory there ([values/README.md](../values/README.md)).

## These files beat the tier defaults

Helm applies `-f` files in order and the last one wins. `common.yaml` and `<app>.yaml` come after dfe-infra's common, cloud and profile files and after `sizing/`, and an app's instance file comes after `common.yaml`. The full order is the values cascade in [docs/architecture.md](../docs/architecture.md).

The profile file is a tier DEFAULT, not a lock. `profile-scale.yaml` declares `clickhouse.mode: cluster`, and declaring `clickhouse.mode: external` in `infra/common.yaml` beats it, and the network policy opens egress to the external service with it.

Moving a mode means moving its endpoint in the same file, `clickhouse.host` for ClickHouse and `kafka.bootstrapServers` for Kafka, because the profile pins those to the in-cluster service names.

## The storage model is chosen once, at deploy

Both data stores take a storage model that is chosen at deploy and rejected afterwards. A model's name is `<family>-<bulk>`: the family says whether data MOVES to the bulk store or is COPIED to it, and the bulk half says what that store is. Kafka defaults to `local`, which changes nothing. ClickHouse defaults to `auto`, which derives `cached-object` from an `objectStore.endpoint` and `local` from none, so an endpoint with no `storageModel` beside it is not a local deployment.

```yaml
# infra/clickhouse-cluster.yaml
clickhouse:
  storageModel: cached-object     # or tiered-block, local, or auto (default)
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

`cached-object` puts ClickHouse parts on an object-store disk behind a local read-through cache, so the PVC stops being the capacity ceiling and the cache stays disposable. `tiered-block` ranks a hot SSD volume over a cold bulk volume and demotes the oldest parts as the hot one fills, with no object store. Data MOVES, so both volumes must be durable. `tiered-object` moves closed Kafka segments to object storage (KIP-405 tiered storage), so the PVC sizes the hot window. Strimzi ships no RemoteStorageManager, so it needs a broker image with a plugin, and the chart fails the render rather than deploying a broker that looks configured and tiers nothing.

`cached-object` and `tiered-object` are opt-in and render-verified, not live-proven. `tiered-block` is live-proven in cluster mode. Every combination, with its status and evidence, is in dfe-infra [docs/deployment/storage.md](https://github.com/hyperi-io/dfe-infra/blob/main/docs/deployment/storage.md).

On AWS the cluster secret names a ClickHouse bucket, so a DFE-run ClickHouse on `auto` derives `cached-object`. The bucket, the storage model and the cache placement then arrive as inline Helm values, which beat this overlay. A deployment that wants `local` on AWS says so before the first deploy, in the deployment dial (`sizing.storage_model: local`).

## Credentials stay out, and the layout keys lock

Object-store CREDENTIALS never appear in these files. Both charts read them from the environment, wired from a Secret the secrets store materialises: seed `<project>/<env>/clickhouse/s3` and `<project>/<env>/kafka/tiered` with `access_key_id` and `secret_access_key`. A credential that lives at a different path or under different field names binds without reseeding: `clickhouse.objectStore.remoteKey` and `kafka.objectStore.remoteKey` name the path, `accessKeyProperty` and `secretKeyProperty` name the fields, and `secretStoreName` selects the store that mounts them. ClickHouse on AWS can take `clickhouse.objectStore.usePodIdentity: true` and use no static key.

The engine holds these as protected vars and rejects a post-deploy edit with the policy that blocked it (`governance/policies/storage-layout.yaml`):

| key | why it locks |
|---|---|
| `clickhouse.mode`, `kafka.mode` | where the data lives, and moving it strands every existing row |
| `clickhouse.storageModel`, `kafka.storageModel` | the on-disk layout, chosen once |
| `clickhouse.objectStore.*`, `kafka.objectStore.*` | the object-store location the existing parts and segments are in |
| `clickhouse.tieredBlock.*`, `kafka.tieredObject.*` | the cold volume holding the sole copy of its data, and the plugin that reaches the bucket |
| `clickhouse.storage.size`, `.storageClass` and the kafka pair | `volumeClaimTemplates` are immutable, so no sync applies it |

A deployment created before this vocabulary keeps its `storage-model.yaml` beside the current file, because the engine never rewrites a policy file that exists. The shipped lock lists the older key spellings as well, so nothing goes unprotected while a deployment is on an older chart.

A holder of `helmvars:override` can still make a deliberate exception, and a direct git commit still gets through: the policy governs the API, not the repo. Changing any of these on a live deployment is a data migration, not a values edit.

Growing a PVC needs `allowVolumeExpansion: true` on the StorageClass and, because `volumeClaimTemplates` are immutable, a StatefulSet recreate. `local-path` has no resize support at all. That is what the storage model exists to avoid, so reach for a non-`local` model before reaching for a bigger disk. The size and class keys are locked for that reason.

dfe-docker is the other way round: `DFE_DATA_ROOT` picks WHICH disk, and a bind mount takes whatever that disk has. Kubernetes locks size and class, and docker locks location.

## Node and broker counts go up, never down

`clickhouse.replicas`, `clickhouse.keeper.replicas` and `kafka.replicas` are accepted upward and rejected downward. Removing a ClickHouse node drops a copy of the data, or the data itself when the cluster is sharded. A Kafka broker takes every partition replica it held unless those are reassigned first. A Keeper ensemble can lose its Raft quorum, which takes every replicated table read-only with it. Do the move, then lower the count.

The check compares what the overlay stack DECLARES before and after, so nothing declared means nothing to compare and the write is accepted. A write that leaves a declared count undeclared is rejected, because the chart default can be lower. CPU and memory move freely in both directions.
