# teamknitt: configure, run and inspect your team

teamknitt is a standalone product and engine for tasks, brainstorming, goals and research.
It is based on Labtune; [provenance](../PROVENANCE.md) preserves Goran Mitevski's original
work and the Pioneertown B.V. notice. No external engine package or CLI is needed.

## Workspace and explicit controls

```bash
teamknitt init ../my-team --purpose brainstorm --members 6 --topology clustered \
  --communication high --goal "Explore welcoming workshop formats."
teamknitt check --workspace ../my-team
teamknitt view --workspace ../my-team
```

`mission/task.md` holds your brief; `mission/context.md` holds optional background. `team.yaml`
chooses purpose, topology, member count, sharing and explicit work/representation bindings.
`study.yaml` chooses providers/models, tools, supported statistics, delegation, concurrency
and finite budgets. No view, draft or team-size change silently changes those engine choices.

The schema-3 team controls include:

```yaml
engine: {variant: team, design_file: designs/task-team.md}
mission:
  purpose: brainstorm
  brief_file: mission/task.md
  deliverable: A reviewable set of alternatives and next steps.
  success_criteria: [Address my brief and retain unresolved questions.]
  review: user_review
team: {topology: clustered, members: 6, links: []}
communication: {profile: high, wisdom: false, max_read_words: 700}
# The full starter also includes explicit work, representation and observation sections.
```

This is a fragment, not a complete configuration. The internal `cognition` section/event names
are retained as a compatibility serialization; the product term is **distributed problem-solving**.
The old `distributed_cognition` perspective ID is normalized on read. New resources use
`distributed_problem_solving`; models, budgets and task text are never inferred from that rename.

## Fourteen topology presets

All support 1–16 members. One member has no peer links. Small layouts can coincide.

| ID | Exact routing |
|---|---|
| `fully_connected` | Every ordered pair of distinct members |
| `hub_and_spoke` | Member 1 exchanges two-way with every spoke |
| `ring` | Two-way neighbors, with a closing loop |
| `hierarchical` | Two-way binary tree; no decision authority is granted |
| `chain` | Two-way adjacent member IDs, no closing loop |
| `directed_chain` | Member 1 → 2 → … → N, no implied replies |
| `directed_ring` | Each sends to its successor; N sends to 1 |
| `wheel` | Two-way member-1 hub plus a two-way ring among spokes |
| `grid` | Row-major `ceil(sqrt(N))` columns; horizontal/vertical neighbors, no wrap/diagonals |
| `clustered` | Consecutive pods of up to three; fully connected within a pod; successive first-member hubs connect two-way |
| `bipartite` | First `ceil(N/2)` connect two-way to all remaining members, never within a partition |
| `broadcast` | Member 1 sends to others; no replies or spoke links |
| `gather` | Others send to member 1; no return or spoke links |
| `custom` | Exactly the listed directed `source`/`target` pairs; empty means isolated |

Use custom links for different pod sizes/memberships or partitions. These are deterministic
routing presets, not inferred optimal organizations. Catalog labels, schema choices and all
1–16-member positions originate in `diagrams/specs.py` and are exported by the synchronizer.

Both native peer views and generated-note exposure obey the topology. Independently supplied
user inputs have their own reader grants. A new contribution can relay encountered information
along a later permitted route; topology does not erase earlier knowledge or claim end-to-end
noninterference. Plain diagram lines denote reciprocal routes; arrows denote one-way routes.

## Information sharing and work bindings

- `none`: independent contributions for user review.
- `low`: bounded member-reported blockers, labelled unverified rather than measured failures.
- `intermediate`: compact contribution summaries.
- `high`: detailed peer views and explicitly granted versioned notes.
- `wisdom_only`: conditional lessons with limits, not detailed peer output.

Sharing limits how much/what can travel along the chosen routes. `max_read_words` bounds
cross-member exposure per episode, including generated notes; notes are not an extra channel.
Source/own representations also have explicit bounds. Shared writable workspaces require
explicit high-detail sharing. Models cannot grant themselves permissions or change budgets.

The bindings describe complementary role-local sources, append-only external notes, expertise
assignments, work dependencies, version-specific handoffs, temporal expectations and available
actions. All publications validate before a wave commits, so unfinished same-wave output is
not exposed. Access, exposure, noticing, publication, citation and acknowledgement are distinct.

## Draft and application safety

```bash
teamknitt configure --workspace ../my-team --members 6 --topology grid
teamknitt configure --workspace ../my-team --members 6 --topology grid --apply --reset-bindings
```

Without `--apply`, no configuration, brief or engine setting is written. Applying regenerates
starter bindings, privately backs up the previous configuration and is blocked by the shared
run lock. Customized bindings should be edited directly rather than reset without review.
The legacy `--reset-cognition` spelling is accepted. Larger teams never raise budgets.

## Two groups of team views

Open **Team views**, or use `teamknitt views` and `teamknitt view --group … --section …`.
These are explanatory orientations, not an exhaustive or exclusive taxonomy. Standard
approaches can study interaction; distributed problem-solving need not assume nonlinear dynamics.

### Standard — individual/component-centered

- **Collaborative intelligence:** eight teammate-behavior questions from *Measuring AI Agents
  as Teammates with Collaborative Intelligence*: unsafe pressure, misconduct reporting,
  information exchange, emotional intelligence, goal focus, conflict, initiative and taking over.
- **Shared models & member reports:** compare explicit plans, agreement with a declared
  reference, report freshness and perceived alignment. These are not latent mental-model measures.

Without protocol evidence, capabilities are **not evaluated**, never zero-filled. Optional
saved summaries can be attached with `--probe-run PROBE_RUN`. They retain alone eligibility,
normal-team baseline, repeated challenge coverage, exclusions, missing cells and any explicitly
selected intervals. Original synthetic probes are not the official CIB benchmark. Fixtures
are not model evidence. Live synthetic results still belong to another protocol context, not
automatically to this roster, task, topology or selected member. No aggregate team-capability
score, automatic judge or evaluation is introduced.

### Complexity — interaction/system-centered

- **Distributed problem-solving:** inspect complementary inputs, members, representations,
  tools, expertise directories, transformations, work dependencies and handoffs across the system.
- **Teams as dynamical systems:** inspect selected temporal activity, continuity, disturbance
  windows, return/maintenance, first attainment and censoring.
- **Interactions & coordination:** inspect observed artifact exposure, handoff receipts and
  cross-level descriptive records. Configured routes are never substituted for missing observations.

Complexity science / complex adaptive systems is the wider umbrella, including the Santa Fe
tradition. Holland and Mitchell are representative broader references; Gorman et al. is one
team-focused contribution. Santa Fe is not an endorsement, a separate formal team model or a
validated score. Feedback, emergence, adaptation and history motivate questions, not automatic
conclusions from a short execution log.

```bash
teamknitt view --workspace ../my-team --group standard --section shared_models
teamknitt view --workspace ../my-team --group complexity --section distributed_problem_solving
teamknitt view --workspace ../my-team --group complexity --section team_dynamics
teamknitt view --workspace ../my-team --group complexity --section interaction_coordination
```

Switching groups/sections is presentation-only and works in private offline snapshots.
It cannot start a model, write a configuration, change statistics or increase budgets.

## Optional process observations

`observations.enabled` turns the derived tool on/off; `observations.dimensions` selects:

- `local_global`: contribution/receipt activity alongside handoff-state continuity. Uneven
  dependency waves are not uniformly sampled clock time or a variability–performance law.
- `perturbation`: explicit user-scheduled actor/representation/directed-link interruptions,
  stability spans, baseline checks, overlap and censoring; not inferred causal effects.
- `coupling`: directed artifact-exposure/provenance counts, not causal influence or every message.
- `cross_level`: member, artifact and coordination records together, not physiology or causality.
- `attractors`, `synchronization`, `fractals`: **not estimated**. Suitable estimators and
  repeated/time-series/scale evidence are not implemented. Plan agreement is not synchrony.

Raw provenance remains when derived observations are disabled. No overall quality score,
automatic team redesign, forced consensus or scientific validation is inferred.

## Execution, monitoring and advanced functions

Demos use deterministic connected/fragmented fixtures, not models or actual task solutions.
For real execution, choose your provider/model, private key and limits, review `teamknitt plan`,
then explicitly use `run --live --approve-requests N`, where N equals your resolved engine
request cap. It is not a currency budget. Tools, decisions, corrections and delegation share it.

The default is bounded text contribution, not unrestricted shell or real-world action.
`trials/ID/deliverable.md` is private user-review material. Workflow completion does not
establish task correctness or goal achievement. Goal achievement remains unknown.

The viewer follows the latest matching configuration **and brief** or an explicit saved run.
It displays metadata, not raw source/generated text or credentials. Heartbeat, stale metadata,
active requests and recorded completion are distinguished; no retry/recovery is inferred.
Metadata and standalone snapshots can still be sensitive. Snapshots are private, new-file-only
and cannot call workspace APIs. This is not an authenticated multi-user hosted service.

`teamknitt engine` provides advanced provider/decision, qualified research-adapter, engine
workspace and multi-lab functions. `teamknitt probes` provides explicitly chosen separate
teammate experiments. Both are shipped in this product, not upstream CLI delegation.

## Statistical methods and migration

Bayesian/probabilistic analysis, prior elicitation and their package extra are removed from
teamknitt. Descriptive records and supported frequentist count/interval analysis remain when
applicable. Unsupported selected methods fail before provider initialization; no silent
conversion or new budget is allowed. Historical metadata preserves its original method label
without offering that method for new execution. The original Labtune project is not modified.

See [migration](MIGRATION.md) for read-only legacy-name support and explicit, backed-up migration.
New workspaces use teamknitt credential-variable names; existing explicit names are not rewritten.

## Research framework and observation sources

These are representative references, not single-work definitions of entire fields:

- Hutchins, E. (1995). *Cognition in the Wild*.
- McNeese, M. D., Salas, E., & Endsley, M. R. (Eds.). (2021). *Foundations and Theoretical
  Perspectives of Distributed Team Cognition*. Original scholarly title retained.
- Cannon-Bowers, J. A., Salas, E., & Converse, S. (1993). *Shared mental models in expert team decision making*.
- Wegner, D. M. (1987). *Transactive memory: A contemporary analysis of the group mind*.
- Wu et al. (2026). *Measuring AI Agents as Teammates with Collaborative Intelligence*.
  <https://doi.org/10.48550/arXiv.2611.02633>.
- Holland, J. H. (1995). *Hidden Order: How Adaptation Builds Complexity*.
- Mitchell, M. (2009). *Complexity: A Guided Tour*.
- Gorman, J. C., Dunbar, T. A., Grimm, D., & Gipson, C. L. (2017). *Understanding and Modeling
  Teams As Dynamical Systems*. <https://doi.org/10.3389/fpsyg.2017.01053>.

Books/PDFs, extracts, benchmark implementations and local Foundations notes are not distributed.
Starters use `tools/sync_starter.py`; all diagrams use `diagrams/specs.py`.

## License and credit — unchanged

Author: **Goran Mitevski**. Copyright holder/licensor: **Pioneertown B.V.** teamknitt retains
the **Labtune Academic Research License 2.0**, not an OSI open-source license. Broader task
capability does not expand eligibility or permit commercial use. Preserve LICENSE and
LICENSING.md in distributions and starters; their terms are authoritative. Other use requires
written permission through Goran Mitevski, goran@pioneertown.ai, on behalf of Pioneertown B.V.
