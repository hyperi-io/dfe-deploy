# sizing/ -- the resolver's committed output for this deployment

`sizing/resolved.yaml` is written by dfe-infra's sizing resolver (`scripts/resolve_sizing.py`) and committed here. It records the tier, focus, cloud, region and ingest estimate the deployment was sized from, its compute cost bucket wherever cloud shapes were resolved, and a `locked:` section. A re-resolve with `--previous` compares each field present in both files and rejects a change without `--migrate`. The fields are partition count, storage model, Kafka provider, KRaft controller mode, cloud and, on a cloud, AZ count.

It is committed on purpose. `dfe-ops upgrade plan --deploy <this repo> --dial deployment.yaml --live` re-resolves and diffs the result against this file, so a re-size is checked against what is deployed rather than derived from scratch. Re-run the resolver and commit what it writes rather than hand-editing this file.

Each run writes `sizing/<tier>.values.yaml`, `sizing/<tier>.report.md` and, wherever Kafka or ClickHouse is sized, `sizing/<tier>.data-charts.values.yaml`. dfe-infra's data ApplicationSet reads that last file straight from this repo, under the `infra/` overlays, so a value in `infra/kafka.yaml` or `infra/clickhouse-cluster.yaml` beats the resolver's. Its platform ApplicationSet reads `sizing/<app>.values.yaml` the same way, such as the `node-pools.values.yaml` that `resolve_sizing.py images` writes.

A report says what was sized, from which ratio, at which confidence and in which cost bucket. OpenTofu's inputs, `sizing.auto.tfvars.json`, belong beside the OpenTofu root module that reads them.

`governance/policies/sizing-locks.yaml` is the engine's side of the same locks: it rejects an API edit to the chart keys behind them unless the caller holds `helmvars:override`, and `storage-layout.yaml` does the same for the storage model. Neither policy holds the Kafka provider or the AZ count, so the resolver alone guards those. A direct git commit gets past both.
