# teamknitt: tasks, ideas, goals and team monitoring

## Product versus engine

teamknitt configures and monitors teams for a user-defined purpose. Labtune is the **engine**,
not a requirement to frame every task as a research lab. Distributed team cognition organizes
how work, information and representations are distributed. The dynamical-systems dimensions
are an optional additional observation tool. The framework does not select a team on performance.

The schema-version-3 `team.yaml` is the user-facing configuration:

```yaml
schema_version: 3
name: My team
engine: {variant: team, design_file: designs/task-team.md}
mission:
  purpose: brainstorm                  # task | brainstorm | goal | research
  brief_file: mission/task.md
  deliverable: A reviewable set of options and next steps.
  success_criteria: [Address my brief and retain important alternatives.]
  review: user_review
team:
  topology: ring                       # fully_connected | hub_and_spoke | ring | hierarchical | custom
  members: 4                           # 1..16
  links: []                            # custom: explicit source/target directed pairs
communication: {profile: high, wisdom: false, max_read_words: 700}
# Explicit cognition, dynamics and observations sections follow in the complete starter.
```

This fragment is not a complete config. The [starter](../examples/task_team/team.yaml) includes
role responsibilities, context, source/workspace grants, work bindings, expertise directory,
version-specific handoffs, temporal reference, capabilities and available actions.

`study.yaml` holds engine provider/model, domain/tool, statistical, delegation, concurrency
and budget choices. teamknitt translates the user's task/count/sharing choices into the
selected Labtune plan **without silently changing those model or budget settings**. The
engine's native six lab designs remain available separately through `labtune` and the advanced
research template. teamknitt's task design is shipped outside that catalogue.

## Start, configure and inspect

```bash
teamknitt init ../my-team --purpose goal --members 4 --topology hub_and_spoke \
  --communication intermediate --goal "Explore practical ways to reach my goal."
teamknitt check --workspace ../my-team
teamknitt view --workspace ../my-team
```

The viewer uses Labtune's warm neutral/brass/ink instrument-panel aesthetic and yellow-on-dark
wordmark treatment, with no external font download. Its builder previews alternate sizes,
topologies, purpose and sharing. Previewing is a read-only local operation; it does not
rewrite a configuration, edit the brief, start a model or increase a budget.

`teamknitt configure` makes the same draft from the CLI. Applying needs both `--apply` and
`--reset-cognition`, because the mechanical starter builder regenerates role/representation/
work bindings. The previous config is privately backed up under ignored `setup/`. The brief
and engine settings are unchanged. Applying waits for the shared engine run lock. If you
customized cognition, edit it directly or review the regenerated draft carefully.

`teamknitt prepare` saves `plans/teamknitt.json`. Planning reads bounded local inputs and
hashes the brief, config and source identities; it does not read keys or call providers.
Changing a brief or config gives a different identity, so the monitor does not mix old goals.

## Communication topology and amount are different controls

- **Fully connected:** every ordered pair of distinct members.
- **Hub-and-spoke:** bidirectional edges between member 1 and each spoke. Spokes can relay
  through the hub in later waves, not directly to one another.
- **Ring:** bidirectional neighbors; a two-member ring has one pair, not duplicate links.
- **Hierarchical:** a bidirectional binary-tree routing layout. It is not an automatic
  command hierarchy, decision rule or allocation of authority.
- **Custom:** exactly the directed `source` / `target` pairs listed. Reverse links are not
  implied. An empty custom graph is isolated, not secretly replaced by full sharing.

Both engine peer views and generated artifact exposure obey the routes. An actor can relay
information it encountered by making a new permitted contribution; topology does not claim
end-to-end noninterference or erase prior knowledge. Independently supplied user inputs have
explicit reader grants and are not peer sends.

Sharing profiles determine how much/what may flow along those routes:

| Profile | Generic user-task behavior |
|---|---|
| `none` | No peer contribution sharing; user reviews independent outputs |
| `low` | Bounded member-reported blockers/constraints; labelled unverified, not measured scientific failures |
| `intermediate` | Compact contribution summaries |
| `high` | Detailed peer views and explicitly granted versioned workspace notes |
| `wisdom_only` | Conditional lessons with stated conditions/limits, without detailed peer output |

The advanced research template retains the engine's evidence-backed dead-end rule for low
research sharing. Generic task blockers must not be confused with those measured receipts.
`max_read_words` bounds cross-member views per episode. Generated artifact text uses the
remaining allowance, not an extra channel. Source/own representations also have their own
explicit word bound. Source text can be role-local; a common goal does not require identical
knowledge. Shared writable workspace grants require explicitly selected high detail. Models
cannot grant themselves access or change topology/budgets.

## What distributed cognition contributes

The main configuration covers context and task structure; member perspectives/responsibilities;
complementary knowledge; external representations and transformations; who is assigned relevant
expertise; work dependencies and handoffs; explicit temporal expectations; and action opportunities
that require capabilities and informational structures. The framework is drawn from the
McNeese–Salas–Endsley volume, not the eight dimensions of a teammate benchmark.

Representations are immutable user text inputs or append-only generated notes. Publications
cite specific versions actually exposed to the actor. Wave outputs validate before commit,
so one member cannot see another's unfinished same-wave response. Handoffs identify producer,
consumer, exact representation version and due phase. A late acknowledgement is distinct from
an on-time one. Missing inputs/receipts/reports stay visible; notes do not prove comprehension.

Temporal plan reports contain an explicit order/deadline and a separate perceived alignment
field. Pairwise report agreement, agreement with a reference, perceived alignment and actual
user-task outcomes are distinct. Different prompts do not establish human cognitive diversity;
expertise labels are assignments, not validated competence. Available/noticed/enacted action
opportunities are recorded separately, not treated as proof of ecological attunement.

See [framework and observation sources](#research-framework-and-observation-sources).

## Optional observation dimensions: Teams as dynamical systems

`observations.enabled` turns the derived tool on/off; `observations.dimensions` selects:

- `local_global`: member contribution/receipt activity and handoff-state continuity. CV/counts
  describe uneven dependency waves, including engine boundaries—not uniform clock-time samples.
- `perturbation`: optional actor/representation/directed-link interruptions, declared stability
  spans, return/maintenance versus first attainment, baseline checks, overlap and censoring.
- `coupling`: directed artifact-exposure/provenance observations, not causal influence estimates.
- `cross_level`: member actions, artifact versions and team coordination side by side—not
  neural/physiological measurements or inferred cross-level effects.
- `attractors`, `synchronization`, `fractals`: visible **not_estimated** states. Suitable
  state-space/oscillatory/scale estimators are not implemented; short uneven traces do not
  establish these constructs. Temporal-plan agreement is not synchronization.

Raw execution/provenance records remain for accountability when the additional derived tool
is disabled. No overall team score, paid judge, automatic topology ranking or organizational
improvement is inferred. `teamknitt observations` lists the concepts and limitations locally.

## Execution, live monitoring and review

`teamknitt demo` uses local deterministic connected/fragmented fixtures; it does not use a
model or solve the user's actual task. It demonstrates work flow and how perceived alignment
can coexist with conflicting explicit plans.

For a real model run, replace the task placeholder, choose your provider/model/private key
and engine limits, then use `run --live --approve-requests N`. N must equal resolved
`budget.max_llm_calls`; neither team size nor a draft raises it automatically. A reference
one-final-response-per-main-episode case is printed in the plan, not promised as a cost bound.
Decision, correction, fallback, delegation and qualified tools use the same inherited limits.
A request cap is not a currency cap.

The default is bounded **text contributions**, not arbitrary code, shell or real-world action
execution. Engine domain adapters retain their own qualification/evidence boundaries. An agent's
claim that a task is done is not accepted as proof of goal achievement.

`teamknitt view --workspace PATH` follows the latest saved/running execution matching the
current configuration **and brief identity**, polling metadata only. The Monitor tab can
switch to setup-only. An explicit `teamknitt view trials/ID` follows that record instead.
Producer heartbeat and telemetry are distinguished; a stale connection is not evidence of
continued work. The viewer cannot start, retry, cancel or pay for a model request.

Private `trials/ID/deliverable.md` contains the actual contributions. `goal_achieved` remains
unknown and `task_review` awaits the user. There is no automatic winner or unsupported claim
of task success. Raw engine records may contain private prompts/text; the viewer omits those
and displays process metadata. Even metadata can be sensitive.

## Research framework and observation sources

- McNeese, M. D., Salas, E., & Endsley, M. R. (Eds.). (2021). *Foundations and
  Theoretical Perspectives of Distributed Team Cognition*. CRC Press. This informs
  the distributed-cognition configuration, not a validated model of LLM cognition.
- Gorman, J. C., Dunbar, T. A., Grimm, D., & Gipson, C. L. (2017). *Understanding and
  Modeling Teams As Dynamical Systems*. Frontiers in Psychology, 8, 1053.
  <https://doi.org/10.3389/fpsyg.2017.01053>. This informs optional process observations,
  not an automatic team-quality score or causal estimator.
- Wu et al. *Measuring AI Agents as Teammates with Collaborative Intelligence*.
  <https://doi.org/10.48550/arXiv.2611.02633>. This is secondary context for optional
  `teamknitt probes`, not the main configuration framework or an official replication.

Source books/PDFs, extracts and the detailed local Foundations write-up are not distributed.
The software's operational records do not validate psychological constructs or task success.

## Files, packaging, rename and license

Run records use the engine's ignored `trials/ID`, plus `team-plan.json`, `team-run.json`,
`cognition-state.json`, metadata `team-telemetry.json` / `team-report.json`, and the private
`deliverable.md`. Interrupted work retains records, not automatic recovery. Config backups,
private inputs, results and snapshots stay out of Git/packages.

The loopback server exposes only its page, metadata state and non-mutating draft endpoint.
No arbitrary file, configuration write, run-start or provider-call route exists. A standalone
HTML snapshot is new-file-only, private and offline; its builder cannot use workspace APIs.
This is not an authenticated multi-user hosted service or a cryptographic audit log.

The distribution and CLI are now **teamknitt**; older unpublished Teamthill package namespaces
are not included. Do not co-install separate distributions owning the same engine packages.
An explicit advanced schema-2 research template is supported with `--template research`;
older optional probes remain separate under `teamknitt probes`, not the main task workflow.
The repository is <https://github.com/JeranRolevs/teamknitt>. Foundations source material
and local foundation notes are ignored and excluded from starters and release artifacts.

Starters use `tools/sync_starter.py`; all flowcharts and runtime topology geometry originate
in `diagrams/specs.py`. LICENSE, LICENSING.md, Goran Mitevski's credit and the Pioneertown B.V.
notice remain unchanged. Broader task capability does **not** expand the license's eligibility
or permit commercial use; read the legal texts and seek written permission when required.
