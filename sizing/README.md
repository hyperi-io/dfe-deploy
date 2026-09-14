# sizing/ -- the resolver's committed output for this deployment

`sizing/resolved.yaml` lands here from a run of dfe-infra's sizing resolver:
the core requirements derived from the ingest estimate, the target-cloud
overlay, the provenance of every ratio it used, the price, the ceiling, and
the six fields `governance/policies/sizing-locks.yaml` refuses to move
without `--migrate`. The values fragments the resolver emits alongside it
merge into `infra/kafka.yaml` and `infra/clickhouse-cluster.yaml`; the tofu
inputs land in `infra/dial.auto.tfvars.json` and
`infra/sizing.auto.tfvars.json`.

`infra/dial.auto.tfvars.json` and `infra/sizing.auto.tfvars.json` are
committed for the same reason: OpenTofu reads them at apply time, so the node
counts and shapes a re-size produces are visible in the diff before anything
is provisioned, not discovered afterwards from what actually got created.

All of it is committed, on purpose: an upgrade or a re-size is then a diff
against what is already here, not a re-derivation from scratch, and the
sizing-locks policy has something concrete to compare a proposed change
against. Re-run the resolver and commit what it writes rather than hand-editing
this file.
