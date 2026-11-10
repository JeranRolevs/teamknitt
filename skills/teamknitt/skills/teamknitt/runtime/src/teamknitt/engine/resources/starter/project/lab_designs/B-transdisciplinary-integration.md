---
schema_version: 1
id: transdisciplinary_integration
name: Transdisciplinary integration
governance: joint_framework
personas:
  - id: structural_modeler
    role: prime
    approach: expose_assumptions_and_build_explanatory_models
  - id: experimental_researcher
    role: prime
    approach: test_mechanisms_and_boundary_conditions
  - id: systems_designer
    role: prime
    approach: construct_and_measure_integrated_solutions
  - id: method_integrator
    role: coordinator
    approach: translate_and_combine_methods_without_erasing_dissent
collaboration:
  procedure: independent_framing_then_framework_workshop
  phases: [independent_framing, translation_workshop, parallel_tests, framework_revision, verification]
  artifacts: [framework, proposals, meetings, candidate_assets]
communication:
  recommended:
    detail: high
    wisdom: {enabled: true}
    mechanisms: [bulletin, framework_workshop, proposal_review]
  on_restriction: adapt_without_escalation
meetings:
  recommended: true
  max_rounds: 2
  max_total_words: 1800
delegation:
  max_depth: 1
  max_children_per_agent: 2
  budget: inherited
decision_tools: inherit
model: inherit
---

# B · Transdisciplinary integration

## Intent and reasoning personas

Co-create a framework that connects the mission's different methods and enables experiments
or solutions that a single track would not have proposed. Method integration is itself a
testable design hypothesis, not evidence of an advantage.

- **Structural modeler:** make terms, mechanisms, assumptions, and constraints explicit.
- **Experimental researcher:** determine what observations distinguish competing explanations
  and where the proposed framework stops predicting useful behavior.
- **Systems designer:** turn cross-method ideas into measurable prototypes and identify
  interface or resource constraints.
- **Method integrator:** translate terminology, surface incompatibilities, and draft common
  concepts. Keep rival models visible rather than replacing disagreement with polished prose.

## Work and collaboration

Begin with independently written frames. Hold a bounded translation workshop using permitted
inputs. Draft a versioned `framework.md` with shared terms, assumptions, links between methods,
open contradictions, and discriminating tests. Teams then run separate tests in parallel.

Revise the framework from observations at checkpoints. Retain earlier versions and predictions
so the lab can check whether integration helped. Changing terminology does not change measured
success. Changes to objectives, data exposure, or evaluator meaning require a new declared
mission/protocol version; they cannot rescue an otherwise failing result invisibly.

## Communication and user choices

Suggested: **high + wisdom**, with short workshops at framing and evidence checkpoints.
Detailed permitted exchanges support method integration; wisdom preserves reusable conditional
lessons without broadcasting a winning recipe as universal advice.

The user may select any level. Intermediate allows broad model connections; low limits exchange
to eligible dead ends. Wisdom-only allows abstract lessons without the full framework. None
retains independent frames and defers joint research synthesis to a separately declared stage.
Record a restricted-sharing variant and which integration activities were limited or inactive.
Never quietly upgrade sharing to preserve the preset's name.

## Disagreement and outputs

If two frameworks conflict, retain both and design a bounded discriminating experiment. If the
budget cannot distinguish them, keep the uncertainty. The integrator does not certify a model
by authoring it. Deliver a verified usable asset plus the framework portions that help apply it.

## Failure modes to watch

Premature convergence, endless terminology negotiation, an integrator dominating every method,
and a shared framework that explains results after the fact but predicts nothing useful.
