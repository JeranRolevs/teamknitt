---
schema_version: 1
id: hub_and_spoke_matrix
name: Hub-and-spoke matrix
governance: central_research_lead
personas:
  - id: research_lead
    role: coordinator
    approach: manage_distinct_tracks_dependencies_and_integration
  - id: creative_track
    role: prime
    approach: explore_alternative_mechanisms_and_problem_frames
  - id: technical_track
    role: prime
    approach: build_and_optimize_concrete_candidates
  - id: measurement_track
    role: prime
    approach: improve_diagnostics_and_test_robustness
collaboration:
  procedure: track_charters_then_bounded_hub_reviews
  phases: [track_charters, parallel_episodes, hub_review, scoped_handoffs, verification]
  artifacts: [proposals, handoffs, meetings, candidate_assets]
communication:
  recommended:
    detail: intermediate
    wisdom: {enabled: true}
    mechanisms: [bulletin, hub_review, handoff, proposal_review]
  on_restriction: adapt_without_escalation
meetings:
  recommended: true
  max_rounds: 1
  max_total_words: 1200
delegation:
  max_depth: 2
  max_children_per_agent: 2
  budget: inherited
decision_tools: inherit
model: inherit
---

# D · Hub-and-spoke matrix

## Intent and reasoning personas

A central research leader coordinates several distinct creative or technical tracks. Track
primes retain methodological ownership and can delegate to bounded child teams.

- **Research lead:** define track charters, identify dependencies and overlaps, propose resource
  allocation and integration tasks, and preserve exploration capacity. Request evidence rather
  than treating confidence or eloquence as performance.
- **Creative track:** generate and test alternate mechanisms, representations, or decompositions.
- **Technical track:** construct candidates, identify bottlenecks, and measure implementation
  tradeoffs under the agreed constraints.
- **Measurement track:** investigate failure mechanisms, comparator quality, and robustness.

The research lead proposes work. The code controller owns resources, permissions, queue state,
and acceptance checks. The lead cannot silently edit these policies or a sealed evaluator.

## Work and collaboration

Start with distinct track charters and protected allocations. Tracks execute independently;
the hub reviews concise permitted packets at checkpoints. Convert dependencies into bounded
handoffs with input/output contracts and provenance. Avoid making every small action wait for
a hub conversation. A blocked track yields capacity while unrelated work continues.

Cross-track tests and component integration get new experiment IDs. Preserve the original
sources and validate the combined result. No central story substitutes for measurements.

## Communication and user choices

Suggested: **intermediate + wisdom**, plus short hub reviews and explicit handoffs. Detailed
implementation transfer requires the user's high-detail artifact permissions or a separately
declared integration stage.

The user can select none, low, high, or wisdom-only. The hub is not an indirect communication
loophole. Even if allowed a broader private review context, its outgoing messages to a track
must not reveal peer information beyond that track's policy. Under none, use predeclared track
charters and operational resource coordination; no peer-derived research advice or live winner
rebasing reaches the primes. Record when cross-track research coordination is inactive.

## Outputs and failure modes

Deliver verified assets with explicit component boundaries and integration evidence. Watch for
a hub bottleneck, starvation of unconventional tracks, serial approval chains, and a central
leader repeatedly forwarding unsupported conclusions.
