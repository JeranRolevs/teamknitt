> Current runtime update — 2026-10-28: bounded live workflows, local decisions and a bundled
> authored-policy memory example are implemented. See [the current scope](https://github.com/JeranRolevs/teamknitt/blob/main/docs/SKELETON.md). Historical design text below may describe earlier stages.

# Selectable lab designs

Updated 2026-10-30: all six presets are available. Design F adds a single scientist with
low, medium and persistent effort, continued contexts and user-selected sequential runs.
See [single-scientist setup](../docs/SINGLE_SCIENTIST.md) for fixed and budget-driven modes.

Date: 2026-10-26. These are ready-made **design Markdown presets** for teamknitt. The plan-only
loader validates and resolves their roles, structural work phases, coordination rules, and
suggested communication settings. Activating those roles in a running lab is a later stage.
See the [skeleton map](https://github.com/JeranRolevs/teamknitt/blob/main/docs/SKELETON.md) for the implementation boundary.

## Choose a design

| Design | How it organizes research | Suggested sharing | Collaboration forms |
|---|---|---|---|
| [A · Multidisciplinary silos](A-multidisciplinary-silos.md) | Specialists pursue separate tracks; compare and integrate later | Low + wisdom | Bulletin, optional final handoff |
| [B · Transdisciplinary integration](B-transdisciplinary-integration.md) | Specialists translate and merge methods into a joint conceptual framework | High + wisdom | Framework workshop, proposal review, roundtable |
| [C · Complementary co-leaders](C-complementary-co-leaders.md) | Two leaders with different reasoning approaches direct their own teams and test disagreements | Intermediate + wisdom | Paired challenge, comparison meeting, handoff |
| [D · Hub-and-spoke matrix](D-hub-and-spoke-matrix.md) | A research lead coordinates distinct specialized tracks and shared dependencies | Intermediate + wisdom | Hub reviews, handoffs, proposal board |
| [E · Flat / holacratic co-lab](E-flat-holacratic-colab.md) | Peers adopt roles and coordinate through bounded meetings and recorded proposals | Intermediate + wisdom | Roundtable, proposal/objection process, rotating facilitation |
| [F · Single scientist](F-single-scientist.md) | One scientist works through user-selected sequences with low, medium or persistent effort | None | Own-context investigation, review and refinement |

These are proposed defaults, not proven best settings. All work toward a usable, verified edge.
They do not require publication, different model providers, or a specialist decision service.

All styles are available in the skeleton; comparisons come later. A preset's labels do not establish different
methods or superior organization. Its resolved task dependencies, output contracts, information
routes, stop rules, and costs must be compared with the executed graph. The
[evidence/comparison notes](https://github.com/JeranRolevs/teamknitt/blob/main/learning_and_evaluation.md) make this distinction explicit.

Design C uses two complementary investigators with different research approaches.
It defines functional reasoning roles, without attempting to reproduce historical personalities.

## What the Markdown activates

Each file has machine-readable YAML front matter and human-readable role instructions. Its
front matter declares:

- a stable ID and schema version;
- the research-governance pattern, distinct from the code controller;
- initial agent personas and the method each contributes;
- the phase sequence and collaboration artifacts;
- recommended horizontal sharing and meeting mechanisms;
- delegation defaults and inherited decision-tool access.

The Markdown body supplies role priorities, collaboration procedures, dissent handling, failure
modes, and observable outputs. An expertise label is a reasoning assignment, not proof that an
LLM has independent professional expertise. Every persona must state uncertainty and support
claims with mission evidence.

The current loader implements the structural part of this sequence; runtime activation and
applying user changes during live work remain interfaces:

1. Parse and validate the declared schema, selected file, and referenced built-in procedures.
2. Apply the mission's hard constraints and the user's overrides to the preset defaults.
3. Resolve personas to actual prime, coordinator, and child-agent contexts. All can use the
   same configured LLM; per-role model overrides remain optional.
4. Compile the effective work graph, delegation limits, communication views, and meeting rules.
5. Record the file contents/hash, resolved configuration, role assignments, and any adaptations
   before starting work. Markdown prose cannot create undeclared tools or execution privileges.

Record the selected preset and resolved settings in configuration history. Users can choose
another style or sharing policy without a performance/acceptance gate. Record when a live
change takes effect and retain prior exposure; a snapshot does not freeze current choices.

Suggested precedence is **mission/runtime limits → explicit user choices → preset suggestions →
base defaults**. A preset must never silently raise a user-selected communication level or budget.

## Selecting a file and overriding it

Supported skeleton configuration; omitted fields inherit defaults:

```yaml
schema_version: 1
lab:
  design_file: lab_designs/B-transdisciplinary-integration.md
communication:
  profile: low
  wisdom: true
meetings:
  max_rounds: 1
  max_total_words: 800
teams:
  max_depth: 2
  max_children_per_agent: 2
model:
  provider: unconfigured
  name: unconfigured
decisions:
  mode: llm_only
```

Use `teamknitt engine --project . plan --design lab_designs/B-transdisciplinary-integration.md
--profile low --wisdom on` from the installed teamknitt checkout (on one line). See
[configuration instructions](https://github.com/JeranRolevs/teamknitt/blob/main/configs/README.md). Planning does not call a model.

Prime count, persona-to-agent assignment, role composition, child count/depth, model, budgets,
communication, meeting cadence, and procedures remain adjustable. If an override removes a
style's defining activity, record the resulting variant. For example, one participating agent
has no peer governance; it must not be reported as a completed multi-party consensus process.

## Communication choice belongs to the user

Keep the existing profiles: none, low, intermediate, high, and wisdom-only. Wisdom can accompany
low/intermediate/high. Internally, detail and wisdom are independent settings; mechanisms below
describe **how** exchange happens, not how much information is permitted.

| User setting | What meetings and shared artifacts may contain |
|---|---|
| None | Operational scheduling only; no peer research, shared rankings, joint research framing, or peer-derived instructions |
| Low | Selected notable dead ends, tested conditions, limitations, and caveats |
| Intermediate | Compact positive/negative findings, broad method descriptions, relevant constraints and objections |
| High | Detailed methods, measurements, permitted artifact references, and scoped proposals |
| Wisdom-only | Conditional abstractions and their applicability/limits; no detailed peer methods, rankings, or solution instructions |

Combining wisdom with a detail level adds its abstract view without weakening the detail cap.
Meetings, leader messages, handoffs, framework updates, and decision-tool responses all obey the
recipient's effective policy. A central research lead cannot use a private view to relay richer
peer information to a restricted track.

A style can recommend rich collaboration while a user selects less sharing. Preserve the user
choice and record an adaptation: reduce the content, defer joint synthesis to a separate declared
integration stage, or disable the affected activity. Do not claim that a restricted-sharing run
performed full transdisciplinary integration or rich peer deliberation when those did not occur.
None-mode operational coordination remains possible; research cooperation is inactive.

## Additional forms of communication

All use versioned Markdown and controller-owned publication. Each has an explicit agenda, allowed
recipients, detail policy, input references, and cost limit. A form does not unlock richer content.

| Form | File or template | Purpose |
|---|---|---|
| Bulletin | Existing `low.md`, `intermediate.md`, `high.md`, optionally `wisdom.md` | Selective asynchronous findings |
| Roundtable / workshop | [meeting.md](../templates/communication/meeting.md) → `meetings.md` | Bounded exchanges, questions, objections, and recorded next work |
| Proposal and objection | [proposal.md](../templates/communication/proposal.md) → `proposals.md` | Costed changes, evidence, dissent, and disposition |
| Shared conceptual framework | [framework.md](../templates/communication/framework.md) → `framework.md` | Versioned terms, assumptions, links between methods, and falsifying tests |
| Paired challenge | [debate.md](../templates/communication/debate.md) → `debate.md` | Compare two explanations and select a discriminating test |
| Handoff | [handoff.md](../templates/communication/handoff.md) → `handoffs.md` | Transfer a bounded task or permitted component with its contract and provenance |

These files are optional collaboration views, not a second evidence store. Full source records
stay with the controller; a meeting's raw transcript is not automatically exposed to all agents.
Low readers receive only eligible dead-end content; wisdom-only readers receive abstractions.
Positive solution proposals, full frameworks, and code transfers are withheld where disallowed.

## Meetings that produce work instead of unbounded discussion

Meetings are bounded tasks scheduled when their input evidence is ready, not always-on chat.
The first implementation can use asynchronous turns. A round proceeds as follows:

1. Participants privately commit their initial position before reading peer arguments.
2. The controller creates a permitted, size-limited packet for each attendee.
3. Each attendee contributes one observation, objection, or costed proposal within the agenda.
4. A facilitator records agreements, unresolved disagreements, and the next test or task.
5. Deterministic scheduling checks resources and dependencies before any proposed work starts.

Set maximum rounds, words/tokens, total calls, cadence, and a finish condition. Facilitation can
rotate; it does not grant authority over evidence or other teams. Unsupported consensus remains
unsupported. Record minority views and unresolved issues rather than forcing agreement.

Decisions about work allocation can use the declared governance procedure. Scientific validity
and asset acceptance remain evidence-based; a vote or a persuasive leader cannot certify them.
One configured LLM can perform all turns. Each agent may use [decision.assess](https://github.com/JeranRolevs/teamknitt/blob/main/decision_tools.md)
for an eligible local question, under its existing context permissions and budget. Configured decision-model judgments remain optional and cannot read another attendee's hidden source record.

## Controller and leader are different roles

The **code controller** owns queue state, resource enforcement, permissions, evidence integrity,
and authoritative publication in every design. A **research leader**, when present, is an LLM
role proposing research direction and coordination. Flat research governance still has a code
controller. A hub's research leader is not an unrestricted controller process.

Spawning children does not create extra budget, voting power, or access. Role reassignment and
changes to the collaboration pattern are versioned. Switching to lower communication cannot
erase prior exposure; start fresh contexts for clean comparisons.

## Extend and compare

Use [the custom design template](_template.md) to add more designs. Custom designs follow the
same mission constraints, one-LLM baseline, evidence rules, optional decision service, and
communication caps. A new name alone is insufficient: describe how task assignment, evidence
exchange, disagreement, and integration differ.

Compare styles with the same mission, total resource budget, model, and confirmation protocol.
Count leadership and meeting costs. Separately test communication-level overrides so a gain
from more tokens or richer sharing is not attributed automatically to a governance style.
