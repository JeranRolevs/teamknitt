---
schema_version: 1
id: flat_holacratic_colab
name: Flat / holacratic co-lab
governance: peer_roles_and_rotating_facilitator
personas:
  - id: exploratory_peer
    role: prime
    approach: discover_new_options_and_reframe_assumptions
  - id: builder_peer
    role: prime
    approach: turn_proposals_into_testable_artifacts
  - id: critical_peer
    role: prime
    approach: challenge_comparisons_and_find_falsifying_tests
collaboration:
  procedure: independent_proposals_then_bounded_peer_coordination
  phases: [independent_proposals, peer_roundtable, task_adoption, parallel_episodes, evidence_review, verification]
  artifacts: [proposals, meetings, handoffs, candidate_assets]
communication:
  recommended:
    detail: intermediate
    wisdom: {enabled: true}
    mechanisms: [bulletin, roundtable, proposal_review]
  on_restriction: adapt_without_escalation
meetings:
  recommended: true
  facilitator: rotating
  max_rounds: 2
  max_total_words: 1500
delegation:
  max_depth: 1
  max_children_per_agent: 2
  budget: inherited
decision_tools: inherit
model: inherit
---

# E · Flat / holacratic co-lab

## Intent and reasoning personas

Peers coordinate research without a permanent scientific leader. Role ownership and bounded
meetings provide structure. The code controller still enforces the mission, resources,
permissions, and evidence requirements.

- **Exploratory peer:** expose assumptions and propose alternative approaches worth testing.
- **Builder peer:** estimate implementation work and produce testable artifacts.
- **Critical peer:** challenge comparators, hidden costs, and unsupported interpretations.

Roles may rotate, combine, or be reassigned through recorded proposals. No persona has general
authority over another prime. Local child delegation remains available, so flat governance among
primes does not forbid children within their individual work teams.

## Meetings and work adoption

Each peer writes its initial proposal before reading the others. A rotating facilitator creates
an agenda from permitted inputs and runs a bounded asynchronous roundtable. Peers can object
with evidence, identify a missing constraint, or suggest a cheaper discriminating test.

The proposal record ends with a task owner, costed test, disposition, and unresolved objections.
Compatible tasks may proceed in parallel. If agreement is not reached within the meeting limit,
the controller uses predeclared scheduling priority and fair allocation among eligible tasks,
or records the item as unresolved if resources are insufficient. No endless consensus loop.

The facilitator has procedural duties rather than research authority. Meeting participation is
per prime team; spawning children does not create additional votes or resource entitlements.
Work-allocation decisions do not establish scientific truth. Asset acceptance uses measurements
and independent confirmation in the same way as every other lab design.

## Communication and user choices

Suggested: **intermediate + wisdom** with short proposal/evidence meetings. High permits detailed
co-design, subject to the same resource and context limits.

Low limits exchanges to eligible failures; wisdom-only permits abstract lessons and their
applicability. None retains operational role/task scheduling but disables peer research
deliberation. Record these restricted variants; do not claim consensus on hidden or unshared
research. Meeting summaries and objections must obey the user's detail setting.

## Outputs and failure modes

Deliver verified usable assets and the minimal coordination record needed to reproduce decisions.
Watch for meeting overhead, ownership gaps, popularity replacing evidence, dominant facilitation,
and collaboration that narrows every prime to the same untested approach.
