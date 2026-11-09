---
schema_version: 1
id: custom_design
name: Custom lab design
governance: custom_declared_procedure
personas:
  - id: first_prime
    role: prime
    approach: specify_a_distinct_testable_method
collaboration:
  procedure: specify_bounded_procedure
  phases: [independent_framing, parallel_episodes, verification]
  artifacts: [candidate_assets]
communication:
  recommended:
    detail: low
    wisdom: {enabled: false}
    mechanisms: [bulletin]
  on_restriction: adapt_without_escalation
meetings:
  recommended: false
  max_rounds: 1
  max_total_words: 600
delegation:
  max_depth: 1
  max_children_per_agent: 1
  budget: inherited
decision_tools: inherit
model: inherit
---

# Custom lab design

## Intent

<Describe what organizational difference this design tests and why it may help the mission.>

## Persona instructions

<For each role, specify its method, priorities, outputs, uncertainty handling, and how it differs
from other roles. Avoid relying only on personality adjectives or expertise labels.>

## Work and collaboration

<Specify task assignment, phase dependencies, evidence exchange, integration, and stop conditions.>

## Disagreement and user overrides

<Specify bounded disagreement handling and what changes under none, low, intermediate, high,
and wisdom-only sharing. Never escalate a user-selected cap automatically.>

## Observable workflow contract

<For each phase, identify input artifacts, responsible role, permitted information, expected
output contract, dependency edges, budget consumption, and stop/abstention behavior. State how
an execution trace would show that the defining collaboration activity actually occurred.>

## Outputs and failure modes

<Describe useful artifacts, verification needs, coordination costs, and what would indicate
that this design is failing. Preserve the common mission and evidence contracts.>
