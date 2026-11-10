# Migration to standalone teamknitt

teamknitt now ships its own engine under `teamknitt.engine`. Only the `teamknitt` package
namespace and command are installed. Based on Labtune; see [provenance](../PROVENANCE.md).
Do not rely on the former `labtune` command/import alias or co-install overlapping old builds.

## Existing team workspaces

Preview first:

```bash
teamknitt migrate --workspace PATH
teamknitt migrate --workspace PATH --apply
teamknitt check --workspace PATH
```

Without `--apply`, no files change. Applying privately backs up original files under ignored
`setup/teamknitt-migrations/`, respects the run lock, and converts legacy engine/perspective
names. A recognized generated `lab.py` launcher becomes `engine.py` using the local engine.
An existing destination or symlink fails closed. Custom launchers/adapters need explicit
manual import updates; migration does not rewrite arbitrary user code.

Briefs, provider/model selections, budget settings and credential files are unchanged. Old
explicit environment-variable names such as `LABTUNE_API_KEY` still work when declared in
that workspace. New workspaces use `TEAMKNITT_API_KEY` / `TEAMKNITT_DECISION_API_KEY`.

Bayesian/probabilistic studies and selected prior workflows are unsupported in teamknitt.
They are rejected before model initialization, not silently changed. Keep originals and
explicitly review any new analysis configuration; the original Labtune project is unaffected.

## Historical records and views

`teamknitt view PATH/trials/ID` verifies original saved bindings before normalizing display
names. It does not rewrite or rerun historical records, infer equivalence with a new
configuration, or change the recorded statistical method. Use explicit paths for legacy
records rather than expecting them to join a new configuration's latest-run cohort.

The previous flat views are reorganized:

- Collaborative intelligence → **Non-system / collaborative intelligence**.
- Shared-plan comparisons → **Non-system / shared models & member reports**.
- Representations, work distribution and handoffs → **System / distributed problem-solving**.
- Dynamics → **System / teams as dynamical systems**.
- Recorded artifact exposure and cross-level records → **System / interactive team cognition & coordination**.

Use `--group non_system|system` and optionally `--section NAME`. Historical
`standard`/`complexity` group choices still map for presentation only. Transactive memory now
has a differentiated/compilational System view; no historical expertise measure is invented. The old `--lens` flag is
accepted with a mapping notice; the former cognition view was split, not declared identical
to one new view. Offline old snapshots remain their original, self-contained presentations.

Requalify any research adapter whose evaluator/worker source changed. No migration makes
provider calls, raises budgets, selects models or certifies task success.

## Human-team background and operator controls (0.6)

The revised [background](TEAM_RESEARCH.md) separates explanatory locus, forms of emergence
and process/state/outcome evidence. It does not convert old telemetry to psychological or
causal measurements. Historical records without an operator controller remain immutable and
cannot be resumed. Main runs created by 0.6 support draft-first `intervene` requests and
explicit future-run `schedule` changes; see [the guide](TEAMKNITT.md#explicit-intervention-controls).
Pause/resume keeps existing limits, stop is terminal, and advanced engine workflows do not
acquire these hooks implicitly. No migration triggers an intervention, model call or restart.
