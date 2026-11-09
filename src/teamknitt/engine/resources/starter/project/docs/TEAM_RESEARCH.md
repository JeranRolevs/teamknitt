# Background: Research and Theory on Human Teams

**Goran Mitevski · 9 November 2026**

This approach draws on human-team research to guide the configuration of LLM-agent teams,
and on dynamical systems theory as a lens for following their work and informing intervention.
This note connects these ideas to Teamknitt's views and controls, without assuming that
findings about human teams transfer to LLM-agent teams.

## Purpose: configure → set tasks → follow work → intervene

teamknitt supports **human-led improvement of AI-agent team(s)**: choose members, roles,
connections, models, tools and bounds; define the work and review criteria; follow recorded
work; intervene explicitly; review what happened at the intended level. Multiple workspaces
can represent different teams. This is not an implemented cross-team optimization service.

Human-team research supplies design hypotheses, not a warrant to attribute human psychology
to agents or to expect the same intervention effects. No automatic team redesign, staffing,
model selection, consensus forcing, statistical-method selection or budget increase occurs.

## Research follow-up

Teamknitt builds on my 2022/2023 thesis research on distributed teams, their creative processes,
and new tools for configuring and refining collaboration in hybrid teams of people and
machine-learning agents. I extend that work to LLM-agent teams, looking at how their structure
shapes interaction, how their work unfolds over time, and how people can intervene. Whether
findings from human teams carry over remains an open research question.

## 1. Three related, separate distinctions

### Explanatory locus: non-system and system

Following the distinction discussed by **Gorman et al. (2017)**:

- **Non-system explanations** locate a phenomenon in member attributes, knowledge, skills,
  or aggregates of individual measures. teamknitt places member-focused Collaborative
  Intelligence evaluation and explicit shared-plan comparisons here.
- **System explanations** locate a phenomenon in situated interaction and organization across
  members and resources, including properties not possessed by one member alone. Distributed
  problem-solving, interactive team cognition, differentiated transactive memory and team
  dynamics provide distinct accounts—not one interchangeable theory.

This is an explanatory orientation, not an exhaustive partition of scholarship, a scientific
quality ranking, or a claim that conventional theories ignore interaction. In particular,
**system is not synonymous with complexity science**, and non-system does not mean every
model is linear. Historical `standard` and `complexity` view URLs/CLI choices map to
`non_system` and `system` for presentation only; historical configurations are not rewritten.

### Form of emergence: composition and compilation

**Kozlowski & Klein (2000)** distinguish compositional emergence—an analogous team-level
construct formed from comparable member-level measures, often using means, sums or
agreement—from compilational emergence: differentiated combinations and patterns without a
simple individual analogue. This distinction is related to, **not identical to**, explanatory
locus. **DeChurch & Mesmer-Magnus (2010)** also highlights cognitive emergence and
measurement issues.

teamknitt exposes configured expertise-holder patterns, work dependencies and artifact flow
where recorded. It does not label a configured pattern, a mean, or a trace as demonstrated
emergence. Agreement requires appropriate comparable observations; missing evidence is unknown.

### Process, state and outcome

**Marks, Mathieu & Zaccaro (2001)** distinguishes what teams **do** from emergent states—how
teams **are**—and organizes processes temporally. Transition phases include planning and
reflection; action phases include execution and coordination. Interpersonal processes can
span both. teamknitt annotates its known configured phases conventionally, not by inferring
interpersonal behavior or altering the scheduler. Unknown/custom phases remain unclassified.

Publications, context exposures and acknowledgements are operational process records. They
are not cohesion, trust, psychological safety, efficacy, potency or shared understanding.
Trust and psychological safety are distinct constructs. None of these states is inferred
from agents' tone, confidence or agreement. Execution completion is not task correctness or
goal achievement; contributions still require human review.

## 2. Inputs, mediators, outcomes and repeated episodes

IPO (**McGrath, 1964; Hackman, 1987**) organizes inputs, processes and outputs. IMOI
(**Ilgen et al., 2005**) includes behavioral **and state mediators**, outcomes feeding later
inputs, history, contingencies and conditional relations. It should not be reduced to an
invariably linear, one-pass pipeline.

teamknitt's episode framing links configured inputs, process metadata, explicitly unmeasured
states, execution status and the human-review boundary. Operator feedback can guide later
work within the same run. A future brief or configuration change requires explicit user action.
There is no automatic episode restart, organizational learning loop or replenished budget.

## 3. Shared, differentiated and distributed accounts

**Shared mental models** (**Cannon-Bowers et al., 1993; Mathieu et al., 2000**) concern
knowledge structures about work and teamwork. Similarity and accuracy are different. Explicit
reported-plan agreement, conformity to a declared reference, freshness and perceived alignment
are separately recorded proxies—not validated latent-model similarity or correctness.

**Transactive memory** (**Wegner, 1987; Lewis, 2003**) concerns differentiated knowledge,
knowing who knows what, and coordinated encoding, storage and retrieval. It is explicitly a
**compilational** account, not merely common knowledge or averaged expertise labels. The new
focused view inspects the configured directory and assigned holders. Credibility,
specialization, successful retrieval and system effectiveness are not measured here.

**Distributed problem-solving** is the product term. **Hutchins (1995)** and the traditions
collected by **McNeese, Salas & Endsley (2021)** motivate inspecting people, artifacts, tools,
procedures and representation transformations together. Original scholarly titles retain their
wording, including *Foundations and Theoretical Perspectives of Distributed Team Cognition*.
**Interactive team cognition** (**Cooke, Gorman, Myers & Duran, 2013**) treats cognition as
situated interaction/activity, not an aggregate of individual mental contents. teamknitt's
interaction view inspects context assembly, artifact transformations and handoff receipts;
those traces do not themselves demonstrate an emergent cognitive capacity.

## 4. Dynamics: useful questions, not already implemented estimators

**Kelso (1995), Schmidt & Richardson (2008), Gorman et al. (2017)** motivate coordination
and dynamical accounts. Complexity science and complex adaptive systems are wider traditions;
Holland, Mitchell and the Santa Fe tradition are additional context, not an endorsement.

- **Local–global stability:** inspect local contribution activity alongside global handoff-state
  continuity. More variability is not automatically flexibility, resilience or better performance.
- **Substrate independence:** task-relevant coupling variables may be studied across different
  physical implementations. This is not proof that human and AI teams share psychology or laws.
- **Cross-level effects:** member, artifact and system records may inform a multilevel study.
  Temporal coexistence does not identify causal direction or improvement at another level.

Continuous time series, recurrence, entropy, synchronization and fractal methods are research
methods, **not implemented estimators here**. Workflow waves are unevenly spaced and contain
different work. Attractors, synchrony, fractals, emergence and adaptation remain not estimated.
Optional disturbance descriptions retain baseline sufficiency, overlap, maintenance/return,
first attainment, right censoring and missingness rather than inventing recovery or causality.

## 5. Intervention: intended mechanism and explicit scope

Human-team literature addresses selection/staffing, role definitions, task design, procedures,
enabling conditions and leadership (**Hackman, 1987, 2002**). Cross-training and
perturbation/adaptive training target different mechanisms (**Gorman, Cooke & Amazeen, 2010**).
**Salas et al. (2008)** synthesizes team-training findings; **Beal et al. (2003)** and
**Edmondson (1999)** address other human-team constructs and relationships. These findings are
not established AI-team intervention effects. Input improvement, process change and outcome
improvement must not be collapsed; transfer across levels is not guaranteed.

| Mechanism / timing | Actual support | Boundary |
|---|---|---|
| Inputs and conditions, between runs | Explicit roles, task/context, success criteria, sources, procedures, topology and sharing | Reviewed reconfiguration, private backup, shared run lock; no automatic staffing/model choices |
| Shared knowledge / role clarification | User-written context, role descriptions and targeted operator feedback | Not human cross-training, latent shared understanding or model-weight training |
| Adaptive-practice design, before a run | Explicit actor, representation or directed-link interruption with a wave and duration | Planned software condition, not a validated human-study replication or causal effect |
| Guidance during a run | Private feedback for chosen future main-member contexts | No new source/tool grants; newest text first within the existing representation word cap; older text can be omitted |
| Execution control | Pause, resume, stop at the next safe dependency-wave boundary | Current-wave work may finish; same run, counters, request cap and wall-time deadline; stop is terminal |
| Outcome review | Private partial/complete deliverable, request receipts and separate outcome evidence | No automatic quality, psychological-state or intervention-effect score |

See [the operator commands](TEAMKNITT.md#explicit-intervention-controls). The browser is an
inspection/command-preparation desk only. Queuing requires explicit CLI `--apply`; starting
metered execution still requires `--live --approve-requests N`. Advanced `teamknitt engine`
workflows, including multi-lab execution, do not acquire these main-run controls implicitly.

**Queued → boundary receipt → context assembly → understanding → outcome** are different
claims. Feedback assemblies are metadata about constructing an actor frame, not proof that a
provider received it or an agent understood/used it. A request arriving after the last useful
boundary is retained as not applied. A stale heartbeat does not establish an active producer.
No automatic retry, crash recovery or cryptographic audit guarantee is claimed.

## Representative sources

The complete structured reference list is available offline with `teamknitt theory` and in
the viewer's Sources & scope section. Setup, planning, tests, diagrams, packaging and all
metadata views make no paid provider calls. Books/PDFs, source extracts, private Foundation
notes, credentials, trials, research results and backups stay outside Git and distributions.

## Provenance and licence

Teamknitt is based on **Labtune**. **Author: Goran Mitevski. Copyright holder/licensor:
Pioneertown B.V.** See [provenance](../PROVENANCE.md).

The **Teamknitt Noncommercial and Research Licence 2.0** governs use:

- General noncommercial, non-research use is free.
- Noncommercial research outside qualifying low-income/lower-middle-income academic institutions
  requires separate written permission. Labtune's research independence, funding and
  anti-circumvention conditions remain.
- Commercial use requires separate written permission through Goran Mitevski, on behalf of
  Pioneertown B.V., at [goran@pioneertown.ai](mailto:goran@pioneertown.ai).

Modification and sharing remain conditional on the permitted uses and distribution terms.
[LICENSE](../LICENSE) is authoritative; [LICENSING.md](../LICENSING.md) explains the conditions.
