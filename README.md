# teamknitt

### Configure the team. Set the task. Follow the work.

**teamknitt** is a standalone product and execution engine for agent teams working on
user-defined **tasks, brainstorming, goals and research**. Choose the members, their
connections, information sharing, models, tools and finite budgets; inspect the process
without assuming that any topology is best or that execution proves success.

Based on **Labtune**, Goran Mitevski's original work. **Author: Goran Mitevski. Copyright
holder/licensor: Pioneertown B.V.** [Provenance](PROVENANCE.md). The runtime is shipped under
`teamknitt.engine`: no separate Labtune installation, import namespace or CLI is required.

## Start with your own direction

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

## Your choices

| Control | Options |
|---|---|
| Purpose | Task · brainstorm · goal · research |
| Members | 1–16, with explicit responsibilities and perspectives |
| Routing | Fully connected · hub-and-spoke · two-way/one-way rings and chains · hierarchy · wheel · grid · clustered pods · bipartite · broadcast · gather · custom |
| Sharing | None · low reported blockers · intermediate summaries · high detailed notes · conditional wisdom only |
| Problem-solving structure | Complementary inputs, scoped representations, expertise directory, work dependencies, handoffs and action opportunities |
| Team views | Standard or Complexity, with focused subviews; presentation-only |
| Execution | Explicit provider/model, domain tools, delegation, concurrency and budgets |

Topology filters both peer views and generated-note exposure. Directed routes do not imply
replies. Hubs and hierarchies do not grant decision authority. Changing a route does not erase
previous exposure, and relay requires later permitted work rather than instant delivery.

```bash
# Draft only: no files, model choices or budgets change.
teamknitt configure --workspace ../my-team --members 6 --topology clustered
# After review, explicitly apply and acknowledge regenerated starter bindings:
teamknitt configure --workspace ../my-team --members 6 --topology clustered \
  --apply --reset-cognition
```

Application keeps a private backup and respects the shared run lock. For customized bindings,
edit the configuration directly rather than resetting it. [Configuration guide](docs/TEAMKNITT.md).

## Two approaches to viewing teams

This is an organizing distinction, not an exhaustive or mutually exclusive taxonomy of research.
The difference is explanatory emphasis—not whether an approach ever studies interactions.

| Group | Focused views | Explanatory focus |
|---|---|---|
| **Standard** | Collaborative intelligence · shared models & member reports | Individual members, their behavior and reports, and decomposed relationships |
| **Complexity** | Distributed problem-solving · teams as dynamical systems · interactions & coordination | Problem-solving across interacting agents, artifacts, tools and time |

*Measuring AI Agents as Teammates with Collaborative Intelligence* informs the **Standard**
behavioral view. Its eight questions are **not evaluated** by ordinary task telemetry. Optional
saved synthetic-probe summaries remain clearly labelled separate-context evidence—not an
official CIB score or a capability claim about the current team. Missing cells remain unknown.

**Distributed problem-solving** is the product terminology for inspecting work across members
and representations. Original scholarly titles retain their wording. Shared-model report
comparisons are under Standard; representation transformations and handoffs are under Complexity.
Agreement, reference conformity, perceived alignment, understanding and correctness stay distinct.

Complexity science and complex adaptive systems are the wider umbrella, including the Santa Fe
tradition. Gorman et al. is one team-focused reference, alongside broader work such as Holland
and Mitchell. Santa Fe is not an endorsement or a validated model. Attractors, synchronization,
fractals, emergence and adaptation are **not inferred** from short uneven execution traces.

```bash
teamknitt views
teamknitt view --workspace ../my-team --group standard --section collaborative_intelligence
teamknitt view --workspace ../my-team --group complexity --section distributed_problem_solving
teamknitt view --workspace ../my-team --group complexity --section team_dynamics
# Optional, already-saved separate protocol; this starts no evaluation:
teamknitt view --workspace ../my-team --group standard --probe-run PROBE_RUN
```

**Bayesian/probabilistic analysis is not an option in teamknitt.** Statistical methods are not
a third theory of teams. Descriptive records and supported frequentist count/interval analysis
remain available when applicable. Unsupported legacy choices are rejected, never silently
converted. This does not change the original Labtune project.

## Try the process offline, then choose whether to run models

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
