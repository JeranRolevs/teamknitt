# teamknitt

### Teamknitt supports human-led improvement of AI-agent team/s. Configure AI agent team/s, set the task or goal, observe and follow the work in different modes, intervene.

Teamknitt is a framework and source-available reference implementation for configuring, observing and intervening in teams of 1–16 LLM agents. Teams work on user-defined tasks, brainstorming and goals; advanced engine workflows also support research missions.

I use human-team research as the organizing lens, without assuming that its findings transfer to LLM-agent teams. Who talks to whom, what they share and how a human can intervene are explicit choices, alongside models, tools and finite budgets.

Based on the approach I developed for Labtune. Teamknitt follows my thesis research on distributed teams and new tools for configuring and refining collaboration in hybrid teams of people and machine-learning agents. [Research background](docs/TEAM_RESEARCH.md#research-follow-up).

Teamknitt ships its own runtime under `teamknitt.engine`; no separate Labtune installation or CLI is required.

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
| Routing | 13 deterministic presets or a custom directed graph — 14 routing options in total |
| Sharing | None · low reported blockers · intermediate summaries · high detailed notes · conditional wisdom only |
| Sources and work | Sources, scoped representations, work dependencies, handoffs, an assigned expertise directory and action opportunities |
| Observation | Non-system and System views, live metadata monitoring and saved/offline snapshots |
| Intervention | Private feedback; safe-boundary pause/resume/stop; explicit planned disturbances |
| Execution | Explicit provider/model, domain tools, delegation, concurrency and budgets |

Routing determines who may receive information; the sharing profile limits what may travel
along those routes. Directed links do not imply replies, and hubs or hierarchies do not grant
decision authority. Changing a route does not erase earlier exposure. Relaying information
requires later permitted work, not instant delivery. Use `teamknitt topologies` for the full catalogue.

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

A collection contains **1–8 separately configured teams** working on the same task. Each keeps
its own models, roles, styles and local limits, within a **single total request cap**. Adding
teams does not raise that cap. Inter-team communication is off by default; when enabled,
bounded designated-member summaries or contributions travel on explicit routes from completed
prior waves. Teams can remain isolated. There is no automatic merge or winning-team selection.

User-selected external URLs (including ub-mode and ponytail) are **references only**, not
imported skills, templates, prompts, code or runtimes. Actual style context must be explicitly
user-authored local text. Repeating a reference for two teams does not merge their identities.
[Multi-team setup, native cloning, routing, limits and intervention](docs/MULTI_TEAM.md).

## Research-informed team views

I use **non-system and system explanations** to organize the team views. I keep this separate
from **compositional and compilational emergence**, and from **processes, states and outcomes**.

IPO and IMOI include feedback and conditional relationships, not just a one-way sequence.
Teamknitt marks transition and action phases, but does not infer interpersonal processes or
psychological states from software traces.
[Research background and references](docs/TEAM_RESEARCH.md).

| Group | Focused views | Explanatory focus |
|---|---|---|
| **Non-system** | Collaborative intelligence · shared models & member reports | Member attributes, behavior, knowledge and aggregates |
| **System** | Distributed problem-solving · transactive memory · interactive team cognition & coordination · team dynamics | Situated interaction, differentiated knowledge and organization across members, artifacts and time |

Both groups show the same recorded process; switching views does not reconfigure the team.
They are explanatory orientations, not quality scores or exclusive scientific camps. System
is not a synonym for complexity science. Historical Standard/Complexity links still resolve.

The records show contributions, permitted information flow, member reports and version-specific
handoffs. Agreement in those records does not establish shared understanding or correctness. **Trust,
psychological safety, cohesion, efficacy, potency and shared understanding remain unmeasured.**
**Transactive memory is differentiated/compilational**, not shared overlap; an assigned expertise
directory is a scaffold, not evidence of retrieval effectiveness.

*Measuring AI Agents as Teammates with Collaborative Intelligence* informs the member-focused
behavioral view. Ordinary task telemetry does **not evaluate** its eight capabilities. Optional
saved probe summaries are separate-context evidence, not an official CIB score or a capability
claim about the current team. I use **distributed problem-solving** as the product term while
retaining original scholarly titles in references.

The dynamics view supports questions about change over time, not estimates of recurrence,
entropy, attractors, synchrony, fractals, emergence or adaptation. Configured routes, observed
exposure, member agreement and task success remain different claims.

```bash
teamknitt theory
teamknitt views
teamknitt view --workspace ../my-team --group non_system --section shared_models
teamknitt view --workspace ../my-team --group system --section transactive_memory
teamknitt view --workspace ../my-team --group system --section interaction_coordination
# Optional, already-saved separate protocol; starts no evaluation:
teamknitt view --workspace ../my-team --group non_system --probe-run PROBE_RUN
```

**Bayesian/probabilistic analysis is not an option in teamknitt.** Descriptive records and
supported frequentist count/interval analysis remain available when applicable. Unsupported
legacy choices are rejected, never silently converted. This does not change the original
Labtune project.

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

Interventions are explicit and human-led:

- **Between runs:** review and apply a configuration change, with a private backup.
- **Before a run:** schedule a disturbance to member, representation or link availability.
- **During a run:** queue private feedback, pause, resume or stop for the next dependency-wave boundary.

The **Intervene** desk prepares commands; the browser does not execute or queue them.
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

**Queued**, **applied**, **assembled**, **understood** and **improved** are separate claims.
A receipt or assembled context does not establish understanding or an intervention effect.
Human-team training findings do not validate benefits for LLM-agent teams.
[Detailed controls and audit boundaries](docs/TEAMKNITT.md#explicit-intervention-controls).

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

Development and sharing are allowed for Permitted Uses, subject to the noncommercial and
research-eligibility conditions, retained notices and same-terms distribution. Instructions
do not waive those conditions; see [contributing](CONTRIBUTING.md).

```bash
python -m pip install -e '.[memory,diagrams]'
python tools/sync_starter.py --check
python tools/sync_skill.py --check
python -m unittest discover -s tests -v
python -m unittest discover -s examples/memory_retention/tests -v
python diagrams/render_flowcharts.py
python -m pip wheel --no-deps . --wheel-dir dist
python tools/check_release.py --artifacts dist
```

All diagrams/catalogs/layouts originate in `diagrams/specs.py`. Starters are synchronized;
credentials, source books, Foundation notes, trials and results stay out of Git and packages.

## Licence

teamknitt uses the **Teamknitt Noncommercial and Research Licence 2.0**, a custom source-available
licence, not an OSI open-source licence. [LICENSE](LICENSE) governs; [LICENSING.md](LICENSING.md)
explains the terms.

- **General noncommercial, non-research use is free.**
- **Research is an exception:** free only for qualifying public/nonprofit academic institutions
  genuinely based in World Bank low-income/lower-middle-income economies and authorized users,
  under Labtune's independence, funding, continuing-eligibility and anti-circumvention rules.
  **Noncommercial research outside those qualifying institutions requires separate permission.**
- **Commercial use requires a separate written licence** from Pioneertown B.V., through
  **Goran Mitevski**, [goran@pioneertown.ai](mailto:goran@pioneertown.ai).
- Use, copying, study, modification and sharing are allowed for Permitted Uses without a software
  licence fee. Retain legal/author/third-party notices, identify changes and distribute software
  changes under the same terms; sharing does not transfer research eligibility or allow commercial use.

**The teamknitt skill has a separate licence.** Anyone may use the unmodified skill in
`skills/teamknitt` with Claude, for any purpose, under the **Teamknitt Skill Licence 1.0**
([licence](skills/teamknitt/LICENSE), [guide](skills/teamknitt/LICENSING.md)). At this stage it
covers Claude only and does not allow changing the skill. It is an additional permission for use
through the skill; the terms above still govern all other use.

**Based on Labtune. Author: Goran Mitevski. Copyright holder/licensor: Pioneertown B.V.**
The research rules override the general noncommercial grant, even for unpaid, personal, nonprofit
or openly published research. Keep LICENSE, LICENSING.md and credits in distributions and starters.
Earlier copies/grants (including version 1.0), existing workspaces, upstream Labtune and third-party
terms are not rewritten. No automatic entitlement check, model choice or budget change is added.
