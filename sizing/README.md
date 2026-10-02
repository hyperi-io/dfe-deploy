# sizing/ -- the resolver's committed output for this deployment

`sizing/resolved.yaml` is written by dfe-infra's sizing resolver (`scripts/resolve_sizing.py`) and committed here. It records the tier, focus, cloud, region and ingest estimate the deployment was sized from, its compute cost bucket wherever cloud shapes were resolved, and a `locked:` section holding the current value of each field the resolver refuses to move without `--migrate`: partition count, storage model, MSK broker type, KRaft controller mode, cloud and AZ count.

It is committed on purpose. `dfe-ops upgrade plan --deploy <this repo> --dial deployment.yaml --live` re-resolves and diffs the result against this file, so a re-size is checked against what is already deployed rather than derived from scratch. Re-run the resolver and commit what it writes rather than hand-editing this file.

The same run writes `sizing/<tier>.values.yaml` and `sizing/<tier>.report.md`. The `kafka` and `clickhouse` blocks of the values file take effect once they are in `infra/kafka.yaml` and `infra/clickhouse-cluster.yaml`, and the report says what was sized, from which ratio, at which confidence and in which cost bucket. The OpenTofu inputs, `sizing.auto.tfvars.json`, belong beside the OpenTofu root module that reads them.

`governance/policies/sizing-locks.yaml` is the engine's side of the same locks: it refuses an API edit to the chart keys behind them unless the caller holds `helmvars:override`, and `storage-layout.yaml` does the same for the storage model. The MSK broker type and the AZ count are OpenTofu inputs with no chart key, so only the resolver guards those. Neither policy governs a direct git commit.
