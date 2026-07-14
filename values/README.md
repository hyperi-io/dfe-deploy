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
