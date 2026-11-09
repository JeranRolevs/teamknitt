# Skeleton configuration

`lab.yaml` is a small user override file. The loader merges it into the packaged
[defaults.yaml](../src/teamknitt/engine/resources/defaults.yaml), validates the
[configuration schema](../src/teamknitt/engine/schemas/lab_config.schema.json), and reads the selected
design's front matter under the [preset schema](../src/teamknitt/engine/schemas/lab_design.schema.json).

Effective priority is explicit CLI/user values, preset suggestions for unset design-specific
settings, then base defaults. Hard structural constraints remain enforced. Unknown fields,
duplicate YAML keys, nonfinite values, invalid counts, project-path escapes, and a confirmation
reserve larger than the total are rejected. A missing specialist is allowed in LLM-only mode.
Selecting a specialist mode names an adapter but does not load it or inspect credentials.

Supported sections:

| Section | Controls |
|---|---|
| `lab` | Project-relative design file |
| `single_scientist` | Design F persistence, sequence count, fixed-pass/budget effort and context policy |
| `model` | One shared provider/name declaration; `unconfigured` works during planning |
| `teams` | Persona instance counts, child/depth overrides, active descendants |
| `resources` | Global active-agent, model-request, and experiment concurrency |
| `budget` | Call/evaluation/time caps, including a confirmation reserve |
| `search` | Independent paths, refinement steps, candidate batch, context policy |
| `communication` | Preset/none/low/intermediate/high/wisdom-only and wisdom override |
| `meetings` | Preset or explicit enablement, round/word limits |
| `decisions` | LLM-only/shadow/selected-active, specialist name, specs, local-call access/limit |
| `statistics` | User-selected supported `frequentist` approach when statistical analysis is needed |
| `domain` | Declared adapter and optional mission file; no evaluation is executed |

For example, a high-sharing style can be inspected with strict isolation:

```yaml
schema_version: 1
lab:
  design_file: lab_designs/B-transdisciplinary-integration.md
communication:
  profile: none
  wisdom: false
teams:
  max_depth: 0
  max_children_per_agent: 0
resources:
  max_active_agents: 2
```

The resulting collaboration plan is marked operational-only for peer coordination. No setting
is silently escalated to preserve the style. `profile: none` plus `wisdom: true` resolves to
wisdom-only. For low/intermediate/high, wisdom on adds the second permitted file. A contradictory
wisdom-only request with wisdom off is rejected.

Persona counts can be changed through `teams.role_instances`, keyed by the selected file's role
IDs. Zero disables a persona; at least one prime must remain. Missing coordinators and single-prime
variants are reported. Counts do not override concurrency or create additional budget. Custom
phases are represented as unbound extensions, never silently treated as implemented procedures.

The compiler's dependencies describe readiness ordering. Its `read_scope` and resolved policy
describe the intended information boundary; neither constitutes implemented runtime access control.

The user can edit these settings and compile another plan directly. A configuration fingerprint
identifies recorded choices without locking them or requiring a promotion gate. The future
runtime will record user changes at explicit effective boundaries and preserve prior exposure.
The skeleton has no automatic lab-optimization or self-improvement settings.

Use `statistics.approach: frequentist` when applicable; Bayesian analysis is not supported. The example/default
is frequentist; no particular test, prior, or decision threshold is imposed. `plan --statistics
frequentist` overrides the file for inspection. The plan remains nonexecuting. Domain adapters
will provide the appropriate protocol and actual results under the
[statistical contract](../statistical_analysis.md).
