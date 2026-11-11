# Human-Team Research in Teamknitt

**Goran Mitevski · 09 November 2026 · rolevski.mk@icloud.com**

Teamknitt draws on research into human teams to guide how LLM-agent teams are configured,
and on dynamical systems theory as a lens for following their work and deciding when to
intervene. This note sets out the research Teamknitt uses, shows how each idea maps onto
Teamknitt's records and controls, and marks where the mapping stops. It does not assume that
findings about human teams transfer to LLM-agent teams; whether they do is the open question
the tool exists to study.

Each numbered section follows the same pattern: the theory, then what Teamknitt records or
exposes in relation to it, then what it does not claim. Readers who already know the theory
can skip to the second and third parts.

## What Teamknitt is for

Teamknitt supports **human-led improvement of AI-agent teams**. A person chooses members,
roles, connections, models, tools and bounds; defines the work and its review criteria;
follows the recorded work as it proceeds; intervenes explicitly; and reviews what happened
at the level they intended. Separate workspaces can represent separate teams. Teamknitt is
not a cross-team optimization service.

## Scope and non-claims

The boundaries below apply throughout and are not repeated in every section.

- Human-team research supplies design hypotheses. It is not a warrant to attribute human
  psychology to agents or to expect the same intervention effects.
- Nothing is automatic. There is no automatic team redesign, staffing, model selection,
  consensus forcing, statistical-method selection, budget increase, episode restart, retry
  or crash recovery, and no cryptographic audit guarantee.
- No psychological state is inferred. Trust, cohesion, psychological safety, efficacy,
  potency and shared understanding are not read from agents' tone, confidence or agreement.
- A record is not a demonstration. Configured patterns, means and traces are exposed as such;
  they are not labelled as emergence, understanding or causal effect. Missing evidence is
  reported as unknown, not as absence.
- Completion is not correctness. Execution finishing is not task correctness or goal
  achievement; contributions still require human review.

## Research follow-up

Teamknitt builds on my 2022/2023 thesis research at Tilburg University, supervised by
T. J. Wiltshire (**Mitevski, 2023**), on distributed software teams, their creative
processes, and creation of new tools for configuring and refining collaboration in hybrid teams of people
and AI agents. I extend that work to LLM-agent teams, treating a team as having
a structural layer that is configured, a relational layer that develops between members
during work, and a dynamical layer visible only in the interaction itself over time.
Teamknitt records what each layer would require for observation and gives people explicit
points of intervention; it does not infer states, estimate dynamics, or diagnose which layer
a breakdown belongs to.

The next research step is to test whether methods from complexity science applied to the
recorded interaction, starting with fractal analysis of contribution and handoff time series,
carry information about team performance. The expectation that they might comes from two
sources. The thesis applied detrended fluctuation analysis to a distributed team's
code-addition series on GitHub and maximal Lyapunov exponents to the daily density of its
discussion, for two periods of the same organization, one that produced a stable product
and one that produced an unstable one. The stable period showed greater long-range
correlation (DFA α ≈ 0.70 against ≈ 0.57, both above a shuffled-surrogate baseline of
≈ 0.50) and more flexible discussion dynamics.

The human-team literature supports the direction while narrowing the expectation. Gorman
et al. (2017) report that the structure of coordination, including its scaling properties,
relates to adaptability. The collaborative problem-solving line (Wiltshire, Butner &
Fiore, 2018; Wiltshire, Steffensen & Fiore, 2019) found relationships with performance that
were specific to moments and trajectories, not to a single global index, and some predicted
relationships were not found at all. The soft-assembly tradition the fractal methods come
from (section 4.2) adds that a scaling exponent is evidence about how a system generates its
behavior, not a score, and that scaling can arise from mechanisms other than the one the
theory proposes. Whether any of this holds for LLM-agent teams, and whether the recorded
traces have the sampling density and stationarity such methods assume, are both open
questions. When these estimators are added they will be marked as research instruments with
their assumptions stated, and section 4 of this note will be revised. Any correlation with
performance depends on a performance measure defined and reviewed by a person, as product
stability was in the thesis, since Teamknitt assigns no automatic quality score.

## 1. Three distinctions that are related but not the same

The literature offers three ways of dividing the field. They overlap, and it is easy to
collapse them into one. Teamknitt keeps them separate.

### 1.1 Explanatory locus: non-system and system

**Gorman et al. (2017)** distinguish two kinds of explanation. **Non-system explanations**
locate a phenomenon in member attributes, knowledge, skills, or aggregates of individual
measures. **System explanations** locate it in situated interaction and organization across
members and resources, including properties that no single member possesses. Within the
system family, distributed problem-solving, interactive team cognition, differentiated
transactive memory and team dynamics are distinct accounts, not one interchangeable theory.

This is an explanatory orientation. It is not an exhaustive partition of scholarship, a
ranking of scientific quality, or a claim that conventional theories ignore interaction.
System is not synonymous with complexity science, and non-system does not mean every model
is linear.

*In Teamknitt.* Member-focused Collaborative Intelligence evaluation and explicit shared-plan
comparisons sit on the non-system side. The interaction, directory and dynamics views sit on
the system side. Historical `standard` and `complexity` view URLs and CLI choices map to
`non_system` and `system` for presentation only; historical configurations are not rewritten.

### 1.2 Form of emergence: composition and compilation

**Kozlowski & Klein (2000)** distinguish **compositional emergence**, in which a team-level
construct is formed from comparable member-level measures by means, sums or agreement and
is analogous to its individual counterpart, from **compilational emergence**, in which the
team-level construct is a differentiated combination or pattern with no simple individual
analogue. This distinction is related to explanatory locus but not identical to it.
**DeChurch & Mesmer-Magnus (2010)** show meta-analytically that cognitive emergent states
predict performance, and that compilational forms predict more strongly than compositional
ones; they also document how much of the literature measures compositionally for reasons of
tractability.

*In Teamknitt.* Configured expertise-holder patterns, work dependencies and artifact flow are
exposed where recorded. Agreement measures require comparable observations and are reported
only where those exist.

*Not claimed.* A configured pattern, a mean, or a trace is not labelled as demonstrated
emergence of either kind.

### 1.3 Process, state and outcome

**Marks, Mathieu & Zaccaro (2001)** separate what teams **do** (processes) from how teams
**are** (emergent states), and organize processes in time. Transition phases include planning
and reflection; action phases include execution and coordination; interpersonal processes
can span both.

*In Teamknitt.* Known configured phases are annotated conventionally. Unknown or custom
phases remain unclassified. The scheduler is not altered by the annotation. Publications,
context exposures and acknowledgements are operational process records.

*Not claimed.* Those records are not cohesion, trust, psychological safety, efficacy, potency
or shared understanding. Trust and psychological safety are distinct constructs and neither is
inferred. Phase annotation does not infer interpersonal behavior.

## 2. Inputs, mediators, outcomes and repeated episodes

The input–process–output model (**McGrath, 1964; Hackman, 1987**) organizes team research
around inputs, processes and outputs. The input–mediator–outcome–input model
(**Ilgen et al., 2005**) adds state mediators alongside behavioral ones, lets outcomes feed
later inputs, and admits history, contingency and conditional relations. It should not be
read as a linear one-pass pipeline.

*In Teamknitt.* An episode links configured inputs, process metadata, explicitly unmeasured
states, execution status and the human-review boundary. Operator feedback can guide later work
within the same run.

*Not claimed.* A new brief or configuration change requires explicit user action. There is no
automatic episode restart, organizational learning loop or replenished budget.

## 3. Shared, differentiated and distributed accounts of team knowledge

**Shared mental models** (**Cannon-Bowers, Salas & Converse, 1993; Mathieu et al., 2000**) are
knowledge structures about the work and about the team that members hold in common.
Similarity and accuracy of those structures are different things and predict performance
differently.

*In Teamknitt.* Explicit reported-plan agreement, conformity to a declared reference,
freshness and perceived alignment are recorded as separate proxies.

*Not claimed.* Those proxies are not validated measures of latent-model similarity or
correctness.

**Transactive memory** (**Wegner, 1987; Lewis, 2003**) is the system by which a team encodes,
stores and retrieves knowledge, including members' awareness of who knows what. It is an
explicitly compilational account: it depends on differentiation, not on common or averaged
knowledge.

*In Teamknitt.* The focused directory view inspects the configured expertise directory and
assigned holders.

*Not claimed.* Credibility, specialization, successful retrieval and system effectiveness, the
components by which transactive memory is usually assessed, are not measured.

**Distributed problem-solving** is the product term for the view that cognition in real work
is spread across people, artifacts, tools, procedures and the transformations of
representations between them. It draws on **Hutchins (1995)** and on the traditions collected
in **McNeese, Salas & Endsley (2021)**, *Foundations and Theoretical Perspectives of
Distributed Team Cognition*. **Interactive team cognition** (**Cooke, Gorman, Myers & Duran,
2013**) goes further and treats team cognition as the interaction itself, an activity rather
than an aggregate of individual mental contents.

*In Teamknitt.* The interaction view inspects context assembly, artifact transformations and
handoff receipts.

*Not claimed.* Those traces do not by themselves demonstrate an emergent cognitive capacity.

## 4. Dynamics: questions the records can support, estimators they do not yet include

**Kelso (1995)**, **Schmidt & Richardson (2008)** and **Gorman et al. (2017)** motivate
treating team coordination as a dynamical process measured continuously rather than relying solely on static measures of team behaviour. The broader theoretical context comes from complexity science and complex adaptive systems, including the work of Holland, Mitchell and the Santa Fe school.

Gorman et al. (2017) organize the approach around three principles. Each suggests a question
the records can be asked, with a caution attached.

- **Local–global stability.** Local contribution activity can be inspected alongside global
  handoff-state continuity. More local variability is not automatically flexibility,
  resilience or better performance.
- **Substrate independence.** Task-relevant coupling variables may be studied across
  different physical implementations. This does not establish that human and AI teams share
  psychology or laws.
- **Cross-level effects.** Member, artifact and system records may inform a multilevel study.
  Temporal coexistence does not identify causal direction or improvement at another level.

### 4.1 Phase transitions and emergence in collaborative problem solving

A second strand applies dynamical tools to teams solving open problems rather than
executing practiced tasks. Its base is the macrocognition-in-teams model (**Fiore et al.,
2010**), which describes collaborative problem solving as moving through phases—knowledge
construction, a team problem model, consensus, evaluation—without saying when a team moves
between them. **Wiltshire, Butner & Fiore (2018)** supplied the dynamical answer: a
transition between phases should appear as a peak in the entropy of coded communication.
Across 40 teams, sliding-window entropy peaks coincided with qualitative shifts in what the
teams discussed, and lower entropy at those points predicted better performance.
**Wiltshire, Steffensen & Fiore (2019)** found movement coordination followed a U-shaped
trajectory over the task, with better teams coordinating more and with a flatter curve.
Earlier, **Wiltshire (2015)** had found synchrony present in dyads but unrelated to
performance; the later work looks at transitions and trajectories rather than global
synchrony for that reason.

The thread through this program is **emergence as an event**. The logic comes from
synergetics and coordination dynamics (**Haken, 1983; Kelso, 1995**): near a phase
transition the current pattern loses stability, variability and disorder rise, and a new
pattern forms that is not derivable from the old one. The entropy peak is that signature
applied to communication. **Schiepek & Strunk's (2010)** dynamic complexity, a measure
built for short, coarse-grained series that rises at critical instabilities, generalizes
it; **Wiltshire, Hudson, Lijdsman, Wever & Atzmueller (2020)** used it on sociometric voice
data to recover task and interaction transitions without transcription or coding. The same
early-warning logic—rising variance, autocorrelation and complexity before a shift—appears
across complex systems (**Scheffer et al., 2009**). On this view emergence is not a state a
team reaches and holds; it is a detectable transition, and what emerges is a new
organization of the interaction. **Gorman et al. (2012)** detect perturbations in real time
from communication dynamics and **Stevens & Galloway (2017)** apply entropy to EEG-derived
team states; both use the same logic on other signals.

**Wiltshire, van Eijndhoven, Halgas & Gevers (2022)** extend the program to human-autonomy
teams. The paper reviews coordination-dynamics approaches and argues that real-time
coordination measures could drive adaptive feedback that regulates a team's coordination,
with phase transitions among its keywords. It is the closest existing statement of a
research agenda for teams that include software agents, and it treats intervention as
something timed to the team's dynamics rather than scheduled in advance.

Philosophically, the strand works under what **van Gelder (1998)** called the nature
version of the dynamical hypothesis—a team *is* a dynamical system, not merely one usefully
described with dynamical tools—where the relational tradition models team-level constructs
as aggregates that supervene on member states. Under the nature version the team-level
pattern is the primary object and constrains members' behavior, which is what Gorman's
cross-level principle asserts and what the philosophy of emergence calls ontological rather
than epistemological emergence. **Gorman (2014)** poses the question directly: whether the
causes of coordination reside within individual minds or between them.

Three lessons bear on relating complexity measures to performance. The quantities that
related to performance were local and temporal—entropy at a transition, the shape of a
coordination curve—not global synchrony. Performance was always a task score defined
independently of the coordination measure. And the measures were applied to coded or
continuously sampled signals with known timing, so their behavior on sparse, unevenly
spaced event records is a separate question.

### 4.2 Soft assembly and interaction-dominant dynamics

Wiltshire's early work and his fractal methods come from an older ecological-dynamical
tradition (**Kugler & Turvey, 1987; Kelso, 1995; Thelen & Smith, 1994**) whose central
concept is the **synergy**: a temporary, task-specific coupling of many components into one
functional unit with few degrees of freedom, **soft-assembled** when a task calls for it,
dissolved after, and not stored in the components. **Riley, Richardson, Shockley &
Ramenzoni (2011)** extended it across people. An interpersonal synergy shows
**dimensional compression** (components move together in a low-dimensional pattern) and
**reciprocal compensation** (a disturbance in one component is offset by others);
compensation is the stronger test, because people can move alike from a shared plan without
any coupling. Wiltshire's (2015) hypotheses—movement synchrony and communicative
complementarity—are these two signatures restated for teams. The tradition's further
commitment is **interaction-dominant dynamics** (**Van Orden, Holden & Turvey, 2003; Kello
et al., 2007**): behavior is produced by interactions across all timescales rather than by
any component, with **1/f or fractal scaling** as the proposed signature. **Wiltshire,
Euler, McKinney & Butner (2017)** tested this in EEG: dimensionality decreased and scaling
exponents increased from rest to task, consistent with soft assembly, though familiarity
raised dimensionality against prediction. The same paper gives the caveat that matters most
here: scaling and soft assembly can each occur without the other, and 1/f scaling has
several generating mechanisms, so an exponent alone establishes neither soft assembly nor
good performance. **Fiore & Wiltshire (2016)** connect the tradition to team cognition by
treating artifacts and technology—offloading and scaffolding—as part of the team process
rather than its context.

For the fractal plan, this strand supplies the hypothesis under test: a team whose behavior
is produced by coupling across timescales should show scaling in its interaction
fluctuations, and a team whose output is the sum of independent contributions should not.
That is a claim about the generating process, testable only against alternative generators.
It is not a claim that a higher exponent means a better team. Mitevski (2023, 2026)
provide the closest empirical precedent (see Research follow-up): in a distributed
software team, the lines-added-per-commit series showed long-range correlation above a
shuffled-surrogate baseline in both periods studied, and more of it in the period that
produced the stable product. Shuffling only establishes that the correlation is not
chance; it does not distinguish an interaction-dominant generator from other sources of
scaling, which is the comparison the plan still has to make.

*In Teamknitt.* Optional disturbance descriptions record baseline sufficiency, overlap,
maintenance or return, first attainment, right censoring and missingness. They do not
invent recovery or causality.

*Not yet implemented.* Continuous time-series analysis, recurrence quantification, entropy,
synchronization and fractal methods are research methods, not estimators present in the
tool. Attractors, synchrony, fractal scaling, emergence and adaptation are not estimated.
Workflow waves are unevenly spaced and contain different kinds of work, which matters for any
method that assumes regular sampling or stationarity. The planned fractal-analysis work
described under Research follow-up will be added here when it exists, with its assumptions
and limits stated.

## 5. Intervention: intended mechanism and explicit scope

The human-team literature addresses selection and staffing, role definition, task design,
procedures, enabling conditions and leadership (**Hackman, 1987, 2002**). Cross-training and
perturbation or adaptive training target different mechanisms (**Gorman, Cooke & Amazeen,
2010**). **Salas et al. (2008)** synthesize team-training findings; **Beal et al. (2003)** and
**Edmondson (1999)** address cohesion and psychological safety respectively. A consistent
finding is that interventions aimed at one level do not reliably reach others: input
improvement, process change and outcome improvement must not be collapsed.

None of these findings is an established AI-team intervention effect. The table maps each
mechanism to what Teamknitt actually supports and where that support ends.

| Mechanism / timing | Actual support | Boundary |
|---|---|---|
| Inputs and conditions, between runs | Explicit roles, task/context, success criteria, sources, procedures, topology and sharing | Reviewed reconfiguration, private backup, shared run lock; no automatic staffing/model choices |
| Shared knowledge / role clarification | User-written context, role descriptions and targeted operator feedback | Not human cross-training, latent shared understanding or model-weight training |
| Adaptive-practice design, before a run | Explicit actor, representation or directed-link interruption with a wave and duration | Planned software condition, not a validated human-study replication or causal effect |
| Guidance during a run | Private feedback for chosen future main-member contexts | No new source/tool grants; newest text first within the existing representation word cap; older text can be omitted |
| Execution control | Pause, resume, stop at the next safe dependency-wave boundary | Current-wave work may finish; same run, counters, request cap and wall-time deadline; stop is terminal |
| Outcome review | Private partial/complete deliverable, request receipts and separate outcome evidence | No automatic quality, psychological-state or intervention-effect score |

See [the operator commands](TEAMKNITT.md#explicit-intervention-controls). The browser is an
inspection and command-preparation desk only. Queuing requires explicit CLI `--apply`;
starting metered execution still requires `--live --approve-requests N`. Advanced
`teamknitt engine` workflows, including multi-lab execution, do not acquire these main-run
controls implicitly.

**Queued → boundary receipt → context assembly → understanding → outcome** are five different
claims, and the records support only the first three. A feedback assembly is metadata about
constructing an actor frame; it is not proof that a provider received it or that an agent
understood or used it. A request arriving after the last useful boundary is retained as not
applied. A stale heartbeat does not establish an active producer.

## Sources cited in this note

The complete structured reference list is available offline with `teamknitt theory` and in
the viewer's Sources & scope section. Setup, planning, tests, diagrams, packaging and all
metadata views make no paid provider calls. Books, PDFs, source extracts, private Foundation
notes, credentials, trials, research results and backups stay outside Git and distributions.

- Beal, D. J., Cohen, R. R., Burke, M. J., & McLendon, C. L. (2003). Cohesion and performance in groups. *Journal of Applied Psychology, 88*(6), 989–1004.
- Cannon-Bowers, J. A., Salas, E., & Converse, S. (1993). Shared mental models in expert team decision making. In N. J. Castellan (Ed.), *Individual and group decision making*. Erlbaum.
- Cooke, N. J., Gorman, J. C., Myers, C. W., & Duran, J. L. (2013). Interactive team cognition. *Cognitive Science, 37*(2), 255–285.
- DeChurch, L. A., & Mesmer-Magnus, J. R. (2010). The cognitive underpinnings of effective teamwork: A meta-analysis. *Journal of Applied Psychology, 95*(1), 32–53.
- Edmondson, A. (1999). Psychological safety and learning behavior in work teams. *Administrative Science Quarterly, 44*(2), 350–383.
- Fiore, S. M., & Wiltshire, T. J. (2016). Technology as teammate: Examining the role of external cognition in support of team cognitive processes. *Frontiers in Psychology, 7*, 1531.
- Fiore, S. M., Rosen, M. A., Smith-Jentsch, K. A., Salas, E., Letsky, M., & Warner, N. (2010). Toward an understanding of macrocognition in teams: Predicting processes in complex collaborative contexts. *Human Factors, 52*(2), 203–224.
- Gorman, J. C. (2014). Team coordination and dynamics: Two central issues. *Current Directions in Psychological Science, 23*(5), 355–360.
- Gorman, J. C., Cooke, N. J., & Amazeen, P. G. (2010). Training adaptive teams. *Human Factors, 52*(2), 295–307.
- Gorman, J. C., Hessler, E. E., Amazeen, P. G., Cooke, N. J., & Shope, S. M. (2012). Dynamical analysis in real time: Detecting perturbations to team communication. *Ergonomics, 55*(8), 825–839.
- Gorman, J. C., Dunbar, T. A., Grimm, D., & Gipson, C. L. (2017). Understanding and modeling teams as dynamical systems. *Frontiers in Psychology, 8*, 1053.
- Haken, H. (1983). *Synergetics: An introduction* (3rd ed.). Springer.
- Hackman, J. R. (1987). The design of work teams. In J. W. Lorsch (Ed.), *Handbook of organizational behavior*. Prentice-Hall.
- Hackman, J. R. (2002). *Leading teams: Setting the stage for great performances*. Harvard Business School Press.
- Hutchins, E. (1995). *Cognition in the wild*. MIT Press.
- Ilgen, D. R., Hollenbeck, J. R., Johnson, M., & Jundt, D. (2005). Teams in organizations: From input-process-output models to IMOI models. *Annual Review of Psychology, 56*, 517–543.
- Kello, C. T., Beltz, B. C., Holden, J. G., & Van Orden, G. C. (2007). The emergent coordination of cognitive function. *Journal of Experimental Psychology: General, 136*(4), 551–568.
- Kelso, J. A. S. (1995). *Dynamic patterns: The self-organization of brain and behavior*. MIT Press.
- Kozlowski, S. W. J., & Klein, K. J. (2000). A multilevel approach to theory and research in organizations. In K. J. Klein & S. W. J. Kozlowski (Eds.), *Multilevel theory, research, and methods in organizations*. Jossey-Bass.
- Kugler, P. N., & Turvey, M. T. (1987). *Information, natural law, and the self-assembly of rhythmic movement*. Erlbaum.
- Lewis, K. (2003). Measuring transactive memory systems in the field. *Journal of Applied Psychology, 88*(4), 587–604.
- Marks, M. A., Mathieu, J. E., & Zaccaro, S. J. (2001). A temporally based framework and taxonomy of team processes. *Academy of Management Review, 26*(3), 356–376.
- Mathieu, J. E., Heffner, T. S., Goodwin, G. F., Salas, E., & Cannon-Bowers, J. A. (2000). The influence of shared mental models on team process and performance. *Journal of Applied Psychology, 85*(2), 273–283.
- McGrath, J. E. (1964). *Social psychology: A brief introduction*. Holt, Rinehart & Winston.
- McNeese, M. D., Salas, E., & Endsley, M. R. (Eds.). (2021). *Foundations and theoretical perspectives of distributed team cognition*. CRC Press.
- Mitevski, G. (2023). *Sparks and fractals: Measuring quantitative aspects of distributed software development team's creative process with Lyapunov exponents and Detrended Fluctuation Analysis* (MSc thesis, supervised by T. J. Wiltshire). Tilburg University.
- Mitevski, G. (2026). Long-range correlation in code commit dynamics as a novel indicator of software product stability: A detrended fluctuation analysis study. arXiv:2605.03574.
- Riley, M. A., Richardson, M. J., Shockley, K., & Ramenzoni, V. C. (2011). Interpersonal synergies. *Frontiers in Psychology, 2*, 38.
- Salas, E., DiazGranados, D., Klein, C., Burke, C. S., Stagl, K. C., Goodwin, G. F., & Halpin, S. M. (2008). Does team training improve team performance? A meta-analysis. *Human Factors, 50*(6), 903–933.
- Scheffer, M., Bascompte, J., Brock, W. A., Brovkin, V., Carpenter, S. R., Dakos, V., Held, H., van Nes, E. H., Rietkerk, M., & Sugihara, G. (2009). Early-warning signals for critical transitions. *Nature, 461*, 53–59.
- Schiepek, G., & Strunk, G. (2010). The identification of critical fluctuations and phase transitions in short term and coarse-grained time series: A method for the real-time monitoring of human change processes. *Biological Cybernetics, 102*(3), 197–207.
- Schmidt, R. C., & Richardson, M. J. (2008). Dynamics of interpersonal coordination. In A. Fuchs & V. K. Jirsa (Eds.), *Coordination: Neural, behavioral and social dynamics*. Springer.
- Stevens, R. H., & Galloway, T. L. (2017). Are neurodynamic organizations a fundamental property of teamwork? *Frontiers in Psychology, 8*, 644.
- Thelen, E., & Smith, L. B. (1994). *A dynamic systems approach to the development of cognition and action*. MIT Press.
- Van Orden, G. C., Holden, J. G., & Turvey, M. T. (2003). Self-organization of cognitive performance. *Journal of Experimental Psychology: General, 132*(3), 331–350.
- van Gelder, T. (1998). The dynamical hypothesis in cognitive science. *Behavioral and Brain Sciences, 21*(5), 615–628.
- Wegner, D. M. (1987). Transactive memory: A contemporary analysis of the group mind. In B. Mullen & G. R. Goethals (Eds.), *Theories of group behavior*. Springer.
- Wiltshire, T. J. (2015). *Team interaction dynamics during collaborative problem solving* (Doctoral dissertation). University of Central Florida.
- Wiltshire, T. J., Euler, M. J., McKinney, T. L., & Butner, J. E. (2017). Changes in dimensionality and fractal scaling suggest soft-assembled dynamics in human EEG. *Frontiers in Physiology, 8*, 633.
- Wiltshire, T. J., Butner, J. E., & Fiore, S. M. (2018). Problem-solving phase transitions during team collaboration. *Cognitive Science, 42*(1), 129–167.
- Wiltshire, T. J., Hudson, D., Lijdsman, P., Wever, S., & Atzmueller, M. (2020). Social analytics of team interaction using dynamic complexity heat maps and network visualizations. arXiv:2009.04445.
- Wiltshire, T. J., Steffensen, S. V., & Fiore, S. M. (2019). Multiscale movement coordination dynamics in collaborative team problem solving. *Applied Ergonomics, 79*, 143–151.
- Wiltshire, T. J., van Eijndhoven, K., Halgas, E., & Gevers, J. M. P. (2022). Prospects for augmenting team interactions with real-time coordination-based measures in human-autonomy teams. *Topics in Cognitive Science, 14*(3), 391–429.

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
