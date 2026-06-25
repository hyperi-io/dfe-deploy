# infra/ -- Argo-watched deployment overlay

Argo CD watches this path. It holds the **scoped-RW** infra overlay for this
environment: which apps run, cluster sizing, pod resources, and cloud specifics.
It is composed over the pinned `dfe-infra` base (`pins.yaml`) via the helm values
cascade -- this overlay wins last.

- `values.yaml` -- the environment overlay (see the sample for the shape).
- At GA these values are **human-authored**.
- At dfe-engine v+0.1, the dfe-* app params/scaling subset becomes
  **engine-authored** into the same file -- the chart wiring does not change, only
  the writer of the value flips (the "source-flip", see dfe-docs).

Do NOT put substrate *deployment* logic here -- that is the `dfe-infra` base. This
overlay only *parameterises* it.
