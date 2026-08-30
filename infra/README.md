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
  `clickhouse-cluster.yaml`, `kafka.yaml`, `cnpg-cluster.yaml`, `ferretdb.yaml`,
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
afterwards:

```yaml
# infra/clickhouse-cluster.yaml
clickhouse:
  storageModel: s3backed          # or local (default)
  s3:
    endpoint: https://my-bucket.s3.ap-southeast-2.amazonaws.com/clickhouse/
    cacheSize: 20Gi
```

```yaml
# infra/kafka.yaml
kafka:
  storageModel: tiered            # or local (default)
  tiered:
    className: io.aiven.kafka.tieredstorage.RemoteStorageManager
    classPath: /opt/kafka/plugins/tiered-storage/*
    config:
      storage.backend.class: io.aiven.kafka.tieredstorage.storage.s3.S3Storage
      storage.s3.bucket.name: my-kafka-bucket
```

`local` is the default and changes nothing. `s3backed` puts ClickHouse parts on
an object-store disk behind a local read-through cache, so the PVC stops being
the capacity ceiling. `tiered` moves closed Kafka segments to object storage
(KIP-405), so the PVC sizes the hot window. Strimzi ships no RemoteStorageManager,
so a tiered deploy needs a broker image carrying a plugin; the chart fails the
render rather than deploying a broker that looks configured and tiers nothing.

Object-store CREDENTIALS never appear in these files. Both charts read them from
the environment, wired from a Secret the secrets store materialises - seed
`<project>/<env>/clickhouse/s3` and `<project>/<env>/kafka/tiered` with
`access_key_id` and `secret_access_key`.

The engine holds these as protected vars and refuses a post-deploy edit with the
policy that blocked it (`governance/policies/storage-model.yaml`):

| key | why it locks |
|---|---|
| `clickhouse.mode`, `kafka.mode` | where the data lives; moving it strands every existing row |
| `clickhouse.storageModel`, `kafka.storageModel` | the on-disk layout, chosen once |
| `clickhouse.s3.*`, `kafka.tiered.*` | the object-store location the existing parts and segments are in |

A holder of `helmvars:override` can still make a deliberate exception, and a
direct git commit still gets through - the policy governs the API, not the repo.
Changing any of these on a live deployment is a data migration, not a values edit.

## Storage size is not the answer

Growing a PVC needs `allowVolumeExpansion: true` on the StorageClass and, because
`volumeClaimTemplates` are immutable, a StatefulSet recreate. `local-path` has no
resize support at all. That is what the storage model exists to avoid, so reach
for `s3backed` / `tiered` before reaching for a bigger disk.

dfe-docker is the other way round: `DFE_DATA_ROOT` picks WHICH disk, and a bind
mount takes whatever that disk has. k8s locks size and class; docker locks
location.
