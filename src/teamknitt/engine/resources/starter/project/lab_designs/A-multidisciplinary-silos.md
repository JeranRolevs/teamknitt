---
schema_version: 1
id: multidisciplinary_silos
name: Multidisciplinary silos
governance: independent_tracks
personas:
  - id: formal_specialist
    role: prime
    approach: derive_structure_and_constraints
  - id: empirical_specialist
    role: prime
    approach: discover_behavior_through_controlled_experiments
  - id: implementation_specialist
    role: prime
    approach: optimize_execution_and_resource_use
collaboration:
  procedure: independent_tracks_then_declared_integration
  phases: [independent_framing, parallel_episodes, independent_verification, optional_handoff]
  artifacts: [track_findings, candidate_assets]
communication:
  recommended:
    detail: low
    wisdom: {enabled: true}
    mechanisms: [bulletin]
  on_restriction: adapt_without_escalation
meetings:
  recommended: false
  max_rounds: 1
  max_total_words: 600
delegation:
  max_depth: 1
  max_children_per_agent: 2
  budget: inherited
decision_tools: inherit
model: inherit
---

# A · Multidisciplinary silos

## Intent and reasoning personas

Keep distinct specialist approaches alive long enough to test them separately. The initial
labels are methodological; adapt their domain vocabulary to the mission.

- **Formal specialist:** derive a model, invariants, bounds, and counterexamples. Prioritize
  assumptions that can be falsified; report where the formalization misses observed behavior.
- **Empirical specialist:** design controlled experiments, examine variation, and test rival
  explanations. Separate exploratory patterns from confirmed effects.
- **Implementation specialist:** study representations, bottlenecks, and execution choices.
  Hold correctness and resource constraints fixed when claiming efficiency gains.

Each prime owns an approach and may delegate bounded work to children. Commit initial plans
before horizontal reads. Children return findings to their own prime.

## Work and collaboration

Run small independent episodes in parallel against the declared comparators. Do not ask primes
to negotiate one shared method during search. Publish only findings permitted by the user's
communication level. Verification compares frozen candidates under the common mission contract.

A later, explicitly declared integration task may combine useful components. Component access
must be authorized for that stage; a none/wisdom-only search must not quietly become a detailed
solution exchange. The integrated candidate receives its own evaluation and confirmation.

## Communication and user choices

Suggested: **low + wisdom**, asynchronous, at episode checkpoints. Low shares notable dead ends;
wisdom shares conditional abstractions. Meetings are normally unnecessary.

All sharing levels remain selectable. None keeps strict research isolation; wisdom-only adds
abstract lessons. Intermediate/high permit more cross-track reuse and should be recorded as
more collaborative variants. Do not assume that the silo pattern is preserved unchanged after
teams begin exchanging full implementations.

## Disagreement and outputs

Conflicting results trigger scoped reproduction or a comparator check. No specialist can
discard another track solely through argument. Preserve distinct promising candidates and
negative findings. Success is a verified usable asset and its applicability limits.

## Failure modes to watch

Duplicate costly work, incompatible output interfaces, late integration surprises, and expertise
labels masking identical underlying methods. Record the actual mechanisms tested and total cost.
