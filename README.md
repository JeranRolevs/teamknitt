# teamknitt

### Configure the team. Set the task. Follow the work.

**teamknitt** is for configuring and monitoring agent teams that work on **user-set tasks,
brainstorm new ideas, explore goals, or conduct research**. You choose the team topology,
member count and how much members can communicate—not just a research-lab preset.

**Labtune is the engine**, supplying bounded execution, model/decision adapters, tool
boundaries, accounting and persistence. teamknitt builds on **Goran Mitevski’s original
Labtune work and idea**, and uses its warm instrument-panel aesthetics. Its organizing
framework remains **distributed team cognition**: work distributed across members,
representations, technology and context. **Teams as dynamical systems** informs change
over time and supplies an **additional, optional observation tool**, not a universal score.

**Author:** Goran Mitevski. **Copyright holder/licensor:** Pioneertown B.V.
[Framework and sources](docs/TEAMKNITT.md#research-framework-and-observation-sources) · [Original Labtune engine](LABTUNE.md).

## Start with your own direction

Python 3.11+:

```bash
python -m pip install -e .
teamknitt init ../my-team --purpose brainstorm --members 4 --topology ring \
  --communication high --goal "Brainstorm welcoming formats for a community workshop."
teamknitt check --workspace ../my-team
teamknitt view --workspace ../my-team
```

The local workspace provides a topology/membership/sharing draft builder and a process
monitor. **Opening it, previewing a draft, planning and observing make no model calls.**
No draft is automatically applied and there is no browser API for starting paid execution.
The user brief is in `mission/task.md`; add background in `mission/context.md`.

## Your team choices

| Control | Choices |
|---|---|
| **Purpose** | Complete a task · brainstorm ideas · work toward a goal · research a question |
| **Members** | 1–16 explicitly selected members; customize their responsibilities and perspectives |
| **Topology** | Fully connected · hub-and-spoke · ring · hierarchical routing · custom directed links |
| **Communication amount** | None · low reported blockers · intermediate summaries · high detailed notes · conditional wisdom only |
| **Communication boundaries** | Directed routes, per-episode read allowance, representation reader/writer grants, optional interruptions |
| **Distributed cognition** | Shared/complementary inputs, externalized work, expertise directory, dependencies, handoffs, explicit plans and available actions |
| **Observation tools** | Select or disable dynamical-systems dimensions without changing the team or running a judge |

Topology restricts **both filtered peer output and generated representation exposure**.
Custom links do not imply reverse links. A hub or hierarchy routes communication; it does
not automatically grant a veto or decision authority. Previously encountered information
is not erased by a later interruption. No topology is ranked or optimized automatically.

```bash
# Draft only; no files change:
teamknitt configure --workspace ../my-team --members 5 \
  --topology hub_and_spoke --communication intermediate --purpose goal
# After review, explicitly apply and regenerate the starter cognition bindings:
teamknitt configure --workspace ../my-team --members 5 \
  --topology hub_and_spoke --communication intermediate --purpose goal \
  --apply --reset-cognition
```

Applying privately backs up the previous `team.yaml`. It does **not** edit your brief,
model/provider settings or engine budgets, and cannot apply while a run owns the workspace.
For custom cognitive arrangements, edit the bindings directly rather than reset them.
[Complete starter](examples/task_team/team.yaml) · [Configuration guide](docs/TEAMKNITT.md).

## Try the process offline, then choose whether to run models

```bash
teamknitt demo --workspace ../my-team --policy connected
teamknitt demo --workspace ../my-team --policy fragmented
```

These deterministic fixtures exercise the engine and demonstrate contribution flow,
handoffs and explicit-plan mismatch. **They do not evaluate a model or solve your task.**
The monitor follows the latest execution matching your configuration and brief; saved
runs can also be inspected with `teamknitt view ../my-team/trials/RUN_ID`.

For actual model execution, explicitly select your provider/model and finite limits in
`study.yaml` (engine settings), supply its private environment key locally, and review:

```bash
teamknitt plan --workspace ../my-team
teamknitt run --workspace ../my-team --live --approve-requests 24
```

Replace `24` with **your own resolved engine request cap**. It is not a recommendation or
currency budget. Larger teams do not raise that limit automatically. Engine decisions,
correction and delegation consume the same cap when explicitly configured.
`trials/RUN_ID/deliverable.md` contains private team contributions for **your review**.
A completed workflow is not proof that the task is correct or that your goal was achieved.

The default is bounded text work. Qualified engine domain tools remain optional; this
release does not add arbitrary shell, external action execution or a human chat platform.

## Distributed cognition first; observations as an additional tool

The configuration framework is informed by *Foundations and Theoretical Perspectives of
Distributed Team Cognition* (McNeese, Salas & Endsley, eds.): role responsibilities,
complementary knowledge, shared representations, who holds relevant expertise, work
interdependencies, handoffs, temporal expectations and action opportunities.

The additional dynamical-systems tool is informed by Gorman et al. (2017):

- **Local/global:** contribution activity alongside handoff-state continuity.
- **Perturbation:** user-scheduled interruptions, response windows and censoring.
- **Coupling:** directed representation exposure/provenance—not inferred causal influence.
- **Cross-level:** member, artifact and coordination observations—not neural effects.
- **Attractors, synchronization, fractals:** explicit **not estimated** states; short,
  uneven workflow waves do not support these inferences, and no such estimator is implemented.

Select dimensions or set `observations.enabled: false` in `team.yaml`.
`teamknitt observations` explains their scope. No aggregate intelligence/quality score,
paid judge, forced consensus or automatic organizational improvement is introduced.
Exposure, understanding, acknowledgement, agreement and correctness remain distinct.

An advanced research-specific template is available with `teamknitt init PATH --template research`.
The older teammate-behavior probes remain isolated behind `teamknitt probes`; they are
not the configuration backbone or the default workflow.

## Development and portability — offline

```bash
python -m pip install -e '.[memory,diagrams]'
python tools/sync_starter.py --check
python -m unittest discover -s tests -v
python -m unittest discover -s examples/memory_retention/tests -v
python diagrams/render_flowcharts.py --diagram 13-teamknitt-system --diagram 14-teamknitt-protocol
python -m pip wheel --no-deps . --wheel-dir dist
python tools/check_release.py --artifacts dist
```

One installable distribution includes teamknitt, its Labtune engine, portable starters and
local viewer. Do not co-install another distribution owning these package namespaces.
Diagram geometry and flowcharts use `diagrams/specs.py`; starters/resources are synchronized.
The product/package/CLI has been renamed from the unpublished Teamthill prototype.
Repository: <https://github.com/JeranRolevs/teamknitt>. Foundations reference material and
local foundation notes are ignored and excluded from starter/package exports.
[Architecture](ARCHITECTURE.md) · [Security](SECURITY.md) · [Contributing](CONTRIBUTING.md).

## License — unchanged; task scope does not widen permission

teamknitt retains the **Labtune Academic Research License 2.0**, not an OSI open-source license.
Free use remains limited to qualifying public/nonprofit academic institutions in World Bank
low-income or lower-middle-income economies and authorized users for independent noncommercial
research. The broader task/brainstorming capability does **not** authorize commercial use.
Company labs, corporate proxies and commissioned company work remain excluded. Company
donations must be unrestricted, without control or privileged research/IP rights. Other use
requires separate written permission through **Goran Mitevski, [goran@pioneertown.ai](mailto:goran@pioneertown.ai),
on behalf of Pioneertown B.V.** Preserve [LICENSE](LICENSE), [LICENSING.md](LICENSING.md) and
both credits in distributions and starters. Research outputs are not relicensed merely
through use. The license texts are authoritative.
