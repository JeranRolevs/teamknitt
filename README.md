# teamknitt

### Teamknitt is a tool for configuring AI agent team/s, where we can set the task, follow the work in different modes, and intervene.

**teamknitt** is a standalone product and execution engine for agent teams working on
user-defined **tasks, brainstorming and goals**. Choose the members, their
connections, information sharing, models, tools and finite budgets; inspect the process
and intervene explicitly without assuming that a topology is best or that execution proves success. Human-team research informs the design, not a validated AI-team improvement claim.

Based on **Labtune** and a follow-up to **Goran Mitevski’s 2022/2023 thesis research** on
distributed teams and their creative processes. [Research background](docs/TEAM_RESEARCH.md#research-follow-up).
**Author: Goran Mitevski. Copyright
holder/licensor: Pioneertown B.V.** [Provenance](PROVENANCE.md). The runtime is shipped under
`teamknitt.engine`: no separate Labtune installation, import namespace or CLI is required.

Work can be followed through member-focused or system-focused views, the live metadata
monitor, and saved/offline snapshots. Switching views does not reconfigure the team.

## Getting started

Python 3.11+:

```bash
python -m pip install -e .
teamknitt init ../my-team --purpose brainstorm --members 4 --topology ring \
  --communication high --goal "Brainstorm welcoming workshop formats."
teamknitt check --workspace ../my-team
teamknitt view --workspace ../my-team
```

Edit `mission/task.md` for your brief and `mission/context.md` for background. Opening the
viewer, previewing a draft, planning and observing make **no provider calls**. There is no
browser API for applying configurations, changing budgets or starting model execution.

## Configuration options

| Control | Options |
|---|---|
| Purpose | Task · brainstorm · goal · research |
| Members | 1–16, with explicit responsibilities and perspectives |
| Routing | Fully connected · hub-and-spoke · two-way/one-way rings and chains · hierarchy · wheel · grid · clustered pods · bipartite · broadcast · gather · custom |
| Sharing | None · low reported blockers · intermediate summaries · high detailed notes · conditional wisdom only |
| Problem-solving structure | Complementary inputs, scoped representations, expertise directory, work dependencies, handoffs and action opportunities |
| Team views | Non-system or System; separate emergence and process/state distinctions |
| Intervention | Private feedback; safe-boundary pause/resume/stop; explicit planned disturbances |
| Execution | Explicit provider/model, domain tools, delegation, concurrency and budgets |

Topology filters both peer views and generated-note exposure. Directed routes do not imply
replies. Hubs and hierarchies do not grant decision authority. Changing a route does not erase
previous exposure, and relay requires later permitted work rather than instant delivery.

```bash
# Draft only: no files, model choices or budgets change.
teamknitt configure --workspace ../my-team --members 6 --topology clustered
# After review, explicitly apply and acknowledge regenerated starter bindings:
teamknitt configure --workspace ../my-team --members 6 --topology clustered \
  --apply --reset-bindings
```

Application keeps a private backup and respects the shared run lock. For customized bindings,
edit the configuration directly rather than resetting it. [Configuration guide](docs/TEAMKNITT.md).

## Multiple teams for one task

```bash
teamknitt teams init ../coding-teams --ids alpha,beta,gamma --members 2 \
  --goal "Propose a CSV validation command-line tool." --request-cap 24
teamknitt teams view --workspace ../coding-teams
# Preview an optional directed communication route; add --apply after review:
teamknitt teams connect --workspace ../coding-teams --profile summaries --source alpha --target beta
```

Each team has independent native configuration, models, styles and local limits. All share
one task and a **single total request cap**, not a cap multiplied by team count. Communication
is off by default. Designated-member summaries/contributions travel only on explicit routes
at prior-wave boundaries. Teams can also remain isolated. No automatic merge or winner.

User-selected external URLs (including ub-mode and ponytail) are **references only**, not
imported skills, templates, prompts, code or runtimes. Actual style context must be explicitly
user-authored local text. Repeating a reference for two teams does not merge their identities.
[Multi-team setup, native cloning, routing, limits and intervention](docs/MULTI_TEAM.md).

## Research-informed team views

Goran's revised **“Background: Research and Theory on Human Teams” (9 Nov 2026)** supplies
three separate distinctions: **non-system/system explanatory locus**, **compositional/
compilational emergence**, and **processes/states/outcomes**. IPO/IMOI includes feedback and
conditional relations—not just a linear pipeline. Transition/action phases are annotated;
interpersonal processes and psychological states are not inferred from software traces.
[Research background and references](docs/TEAM_RESEARCH.md).

| Group | Focused views | Explanatory focus |
|---|---|---|
| **Non-system** | Collaborative intelligence · shared models & member reports | Member attributes, behavior, knowledge and aggregates |
| **System** | Distributed problem-solving · transactive memory · interactive team cognition & coordination · team dynamics | Situated interaction, differentiated knowledge and organization across members, artifacts and time |

These are explanatory orientations, not exhaustive, exclusive scientific camps or quality
scores. System is not a synonym for complexity science. Compositional and compilational
emergence are a related but different axis. Historical Standard/Complexity links still resolve.

*Measuring AI Agents as Teammates with Collaborative Intelligence* informs the member-focused
behavioral view. Ordinary task telemetry does **not evaluate** its eight capabilities. Optional
saved probe summaries remain separate-context evidence, not an official CIB score or capabilities
attributed to this task team. **Transactive memory is differentiated/compilational**, not shared
overlap; its configured directory is not a validated effectiveness measure.

**Distributed problem-solving** is the product term; original scholarly titles retain their
wording. Agreement, reference conformity, perceived alignment, understanding and correctness
remain distinct. Trust, psychological safety, cohesion, efficacy and potency are not measured.
Local–global, substrate-independence and cross-level principles motivate research questions;
recurrence, entropy, attractors, synchrony, fractals, emergence and adaptation are not estimated.

```bash
teamknitt theory
teamknitt views
teamknitt view --workspace ../my-team --group non_system --section shared_models
teamknitt view --workspace ../my-team --group system --section transactive_memory
teamknitt view --workspace ../my-team --group system --section interaction_coordination
# Optional, already-saved separate protocol; starts no evaluation:
teamknitt view --workspace ../my-team --group non_system --probe-run PROBE_RUN
```

**Bayesian/probabilistic analysis is not an option in teamknitt.** Statistical methods are not
a third theory of teams. Descriptive records and supported frequentist count/interval analysis
remain available when applicable. Unsupported legacy choices are rejected, never silently
converted. This does not change the original Labtune project.

## Offline demonstration and execution

```bash
teamknitt demo --workspace ../my-team --policy connected
teamknitt demo --workspace ../my-team --policy fragmented
teamknitt plan --workspace ../my-team
# Explicitly authorize your chosen settings. Replace 24 with your resolved request cap:
teamknitt run --workspace ../my-team --live --approve-requests 24
```

Demos are deterministic software fixtures, not model evaluations or solutions to your task.
The cap is not a currency estimate. Larger teams do not raise it automatically; tools,
decisions, corrections and delegation share the same limits. Private contributions are in
`trials/ID/deliverable.md` for your review. No overall team-quality score or automatic
organizational improvement is produced. The default is bounded text work, not unrestricted
shell or real-world action execution.

## Interventions and outcome review

The **Intervene** desk separates conditions/configuration, planned disturbances, active-run
controls and human outcome review. The browser prepares commands only; it cannot apply them.
From your workspace directory:

```bash
# Preview only; add --apply after review to queue each selected request.
teamknitt intervene trials/RUN_ID --action feedback --message-file mission/feedback.md \
  --actors member.1
teamknitt intervene trials/RUN_ID --action pause
teamknitt intervene trials/RUN_ID --action resume
teamknitt intervene trials/RUN_ID --action stop

# A future-run condition, not an active-run configuration edit:
teamknitt schedule --workspace . --id reviewed-gap --kind actor_unavailable \
  --target member.1 --at-wave 4 --duration 1
```

Requests are bound to one run/configuration and acknowledged before the **next dependency
wave**; current-wave work may finish. Feedback is private, targeted and bounded. Pausing
retains the same lock, model, request counters and original wall-time deadline. Stopping is
terminal, preserves partial contributions and does not run completed-study confirmation.
No active-run model, permission, statistical-method or budget changes are introduced.

Queue acceptance, boundary application, context assembly, understanding and improvement are
separate claims. Human cross-training or adaptive-training findings do not establish AI-team
benefits. [Detailed controls and audit boundaries](docs/TEAMKNITT.md#explicit-intervention-controls).

## Standalone engine and compatibility

`teamknitt engine` exposes advanced execution, provider connection, research adapters, engine
workspaces and multi-lab workflows. Task users normally use the main commands above. Optional
teammate experiments remain under `teamknitt probes`; neither approach group starts them.

Existing workspace model bindings and environment-variable names remain explicit. New
workspaces use `TEAMKNITT_API_KEY` and, if selected, `TEAMKNITT_DECISION_API_KEY`. Preview a
legacy-name migration with `teamknitt migrate --workspace PATH`; only `--apply` writes changes
and creates a private backup. Historical records remain immutable and can be viewed by explicit
run path. [Migration](docs/MIGRATION.md) · [Architecture](ARCHITECTURE.md) · [Security](SECURITY.md).

## Development and portability — offline

The licence does not grant software-modification or redistribution rights. Development and
contribution instructions are for the licensor and separately authorized contributors, not
an additional permission; see [contributing](CONTRIBUTING.md).

```bash
python -m pip install -e '.[memory,diagrams]'
python tools/sync_starter.py --check
python -m unittest discover -s tests -v
python -m unittest discover -s examples/memory_retention/tests -v
python diagrams/render_flowcharts.py
python -m pip wheel --no-deps . --wheel-dir dist
python tools/check_release.py --artifacts dist
```

All diagrams/catalogs/layouts originate in `diagrams/specs.py`. Starters are synchronized;
credentials, source books, Foundation notes, trials and results stay out of Git and packages.

## Licence

teamknitt uses the **Teamknitt Noncommercial Licence 1.0**, a custom source-available licence,
not an OSI open-source licence. [LICENSE](LICENSE) is authoritative; [LICENSING.md](LICENSING.md)
explains the terms.

- Any noncommercial purpose is permitted. The specified personal uses must have no anticipated
  commercial application.
- Use by the listed charitable, educational, public-research, public-safety/health,
  environmental-protection and government organizations is for a permitted purpose regardless
  of funding source or resulting obligations. There is no geographic or academic-only test.
- **The copyright licence does not grant redistribution, software changes or derivative works,
  even for noncommercial purposes.** No sublicensing or transfer is granted. Fair-use rights remain.
- A patent licence, patent-defense termination, a conditional 32-day cure on first written
  notice, and as-is/no-liability terms apply as specified in LICENSE.

**Author: Goran Mitevski. Copyright holder/licensor: Pioneertown B.V. Based on Labtune.**
For permissions outside the grants, contact [goran@pioneertown.ai](mailto:goran@pioneertown.ai).
Keep both legal documents and credits in licensor-authorized distributions and new starters;
that does not grant recipients redistribution rights. Earlier copies/grants and the separate
Labtune upstream licence are not rewritten. Third-party terms remain separate.
