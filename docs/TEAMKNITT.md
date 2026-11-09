# teamknitt: configure teams, set tasks, follow work and intervene

Teamknitt is a tool for configuring AI agent team/s, where we can set the task, follow the work in different modes, and intervene.

Teamknitt is a standalone product and engine for tasks, brainstorming and goals, based on Labtune.
Teamknitt follows my thesis research on distributed teams and their creative processes.
[Research background](TEAM_RESEARCH.md#research-follow-up) ·
[Provenance](../PROVENANCE.md). Goran Mitevski’s author credit and the Pioneertown B.V.
notice are preserved. No external engine package or CLI is needed.

Member-focused and system-focused views, live metadata monitoring and saved/offline snapshots
are different ways to follow the same work. Advanced research commands remain available separately.

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

## Research-informed team views

Open **Team views**, or use `teamknitt views` and `teamknitt view --group … --section …`.
These are explanatory orientations, not an exhaustive or exclusive taxonomy. Non-system
approaches can study interaction; distributed problem-solving need not assume nonlinear dynamics.

### Non-system — member/component-centered explanations

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

### System — interaction/configuration-centered explanations

- **Distributed problem-solving:** inspect complementary inputs, members, representations,
  tools, expertise directories, transformations, work dependencies and handoffs across the system.
- **Transactive memory:** differentiated/compilational expertise patterns, assigned holders and
  retrieval scaffolds, not shared overlap or a validated system-effectiveness measure.
- **Teams as dynamical systems:** inspect selected temporal activity, continuity, disturbance
  windows, return/maintenance, first attainment and censoring.
- **Interactive team cognition & coordination:** inspect observed artifact exposure, handoff receipts and
  cross-level descriptive records. Configured routes are never substituted for missing observations.

Complexity science / complex adaptive systems is a wider tradition for the dynamics view, not
a synonym for all system explanations. It includes the Santa Fe
tradition. Holland and Mitchell are representative broader references; Gorman et al. is one
team-focused contribution. Santa Fe is not an endorsement, a separate formal team model or a
validated score. Feedback, emergence, adaptation and history motivate questions, not automatic
conclusions from a short execution log.

```bash
teamknitt view --workspace ../my-team --group non_system --section shared_models
teamknitt view --workspace ../my-team --group system --section distributed_problem_solving
teamknitt view --workspace ../my-team --group system --section team_dynamics
teamknitt view --workspace ../my-team --group system --section interaction_coordination
```

Switching groups/sections is presentation-only and works in private offline snapshots.
It cannot start a model, write a configuration, change statistics or increase budgets.

The companion [Background: Research and Theory on Human Teams](TEAM_RESEARCH.md),
**9 Nov 2026 · @Goran**, distinguishes explanatory locus from compositional/compilational
emergence and processes/states/outcomes. IPO/IMOI includes feedback and conditional relations.
The Sources & scope page shows the three axes, configured phase annotations and explicitly
unmeasured emergent states. Cohesion, trust, psychological safety, efficacy and potency are
not inferred. Shared-plan comparisons and expertise directories are operational scaffolds.
Historical `standard`/`complexity` view choices map read-only to `non_system`/`system`.

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

## Explicit intervention controls

The **Intervene** desk is a research-informed command-preparation and receipt-inspection page,
not a configuration-write or execution API. Run commands **from the chosen workspace**.
Inputs/conditions, shared-knowledge guidance, adaptive-practice design and run safeguards target
different mechanisms. Human findings do not establish effects for AI teams or across levels.

```bash
# Write private guidance in mission/feedback.md (UTF-8 .md/.txt, at most 12 KB).
# All examples preview only. Add --apply after reviewing scope to queue a request.
teamknitt intervene trials/RUN_ID --action feedback --message-file mission/feedback.md --actors member.1
teamknitt intervene trials/RUN_ID --action pause
teamknitt intervene trials/RUN_ID --action resume
teamknitt intervene trials/RUN_ID --action stop
# Read the queued/applied/exposure metadata, without message text:
teamknitt report trials/RUN_ID
```

- **Feedback:** omit `--actors` to choose all configured main members; otherwise provide a
  comma-separated list of configured IDs. Newest feedback takes priority within the existing
  `cognition.memory.max_words_per_representation` cap; older text may be truncated or omitted.
  Feedback is user task context, never authority to alter model/tool/source/statistical/budget
  settings. Children get no new workspace grants. Existing delegated context rules still apply.
- **Pause:** the already-approved current dependency wave may finish. Before the next wave,
  the runtime acknowledges the request and waits, holding the same shared run lock. Heartbeat
  monitoring continues. The original wall-time deadline **continues to elapse**.
- **Resume:** releases a pause in the same process, run and configuration, with unchanged
  counters and limits. It is not a restart, new approval, crash recovery or renewed budget.
- **Stop:** no new dependency wave starts after boundary acknowledgement. Stops are terminal;
  partial contributions/outputs are preserved for review, never marked completed/confirmed.
  It is not an immediate cancellation of in-flight provider calls or current-wave tools.

A request arriving after the last useful boundary is recorded as not applied. After a stop,
subsequent queued commands cannot resume it. Terminal/legacy records cannot receive active
controls. These controls belong to main `teamknitt run`/`demo` workflows, not implicitly to
advanced `teamknitt engine` single-scientist or multi-lab execution.

Each private request binds its run and configuration. Receipts distinguish preview, queued,
boundary application/rejection and feedback context assembly. Text stays in private run files;
metadata includes recipients, timestamps, hashes, boundary waves and assembly counts, not
message bodies. Assemblies are not proof of provider delivery, understanding, agreement,
correctness, a measured psychological state or a causal intervention effect. The file queue
is bounded (256 requests/run; 64 pending), not a cryptographic or multi-user authorization
system. Stale metadata is not proof of a live producer. No automatic retries/recovery occur.

### Planned disturbances before a run

```bash
# Draft only. Add --apply after review to persist one schedule with a private backup.
teamknitt schedule --workspace . --id member-gap --kind actor_unavailable --target member.1 --at-wave 4 --duration 1
teamknitt schedule --workspace . --id context-gap --kind representation_unavailable --target context --at-wave 4 --duration 1
teamknitt schedule --workspace . --id route-gap --kind link_dropout --target 'member.1->member.2' --at-wave 4 --duration 1
```

Targets and duration must fit the actual configured system and workflow. No kind, target or
wave is chosen from performance automatically. Application preserves task text, role/work
bindings and engine settings, uses a private backup and is blocked during active/paused runs.
The changed identity applies to a future explicit run, not a historical record. Scheduled
conditions are software disturbances, not model-weight training or validated human adaptive
training. To remove/change a schedule, edit `team.yaml` between runs and check the plan.

Review the private deliverable and your chosen outcome criteria separately. A recorded
process change, a better input, reported alignment and an outcome improvement are different
claims. Comparison conditions, independent outcome evidence and analysis choices are yours;
chronology alone cannot identify a causal effect. See [the research background](TEAM_RESEARCH.md).

## Statistical methods and migration

Bayesian/probabilistic analysis, prior elicitation and their package extra are removed from
teamknitt. Descriptive records and supported frequentist count/interval analysis remain when
applicable. Unsupported selected methods fail before provider initialization; no silent
conversion or new budget is allowed. Historical metadata preserves its original method label
without offering that method for new execution. The original Labtune project is not modified.

See [migration](MIGRATION.md) for read-only legacy-name support and explicit, backed-up migration.
New workspaces use teamknitt credential-variable names; existing explicit names are not rewritten.

## Research framework and observation sources

These are representative references, not single-work definitions of entire fields.
`teamknitt theory` contains the expanded bibliography: McGrath, Hackman, Ilgen et al.,
Marks et al., Kozlowski & Klein, Beal et al., Edmondson, Mathieu et al., Lewis,
DeChurch & Mesmer-Magnus, Cooke et al., Kelso, Schmidt & Richardson, Gorman et al.
and Salas et al. See [the integrated background](TEAM_RESEARCH.md).

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

## Licence and credit

Author: **Goran Mitevski**. Copyright holder/licensor: **Pioneertown B.V.** Based on Labtune.
The **Teamknitt Noncommercial and Research Licence 2.0** governs use, not an OSI open-source
licence. General noncommercial, non-research use is free. Research is an exception: free only
for qualifying public/nonprofit academic institutions genuinely based in currently qualifying
World Bank low-income/lower-middle-income economies and authorized users under Labtune's
independent-research, funding, continuing-eligibility and anti-circumvention conditions.
**Noncommercial research outside those qualifying institutions requires separate permission.**
Commercial use also requires a separate written licence from Pioneertown B.V., through
Goran Mitevski, goran@pioneertown.ai.

Use, copying, study, modification and sharing are permitted conditionally for Permitted Uses
without a software licence fee. Retain LICENSE, LICENSING.md, author/copyright and third-party
notices, identify changes and distribute software changes under the same terms. Recipients
must qualify for their own intended uses; a copy, academic account or mode label is not an
exemption. Fair use, reserved rights, automatic termination/written reinstatement and warranty/
liability limits apply. Earlier grants (including version 1.0), existing workspaces, the separate
Labtune upstream licence and third-party terms are not rewritten; see LICENSING.md.
