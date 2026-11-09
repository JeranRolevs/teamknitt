---
schema_version: 1
id: single_scientist
name: Single scientist
governance: single_scientist
personas:
  - id: scientist
    role: prime
    approach: investigate_implement_test_and_critically_revise_own_work
collaboration:
  procedure: sequential_single_scientist
  phases: [investigate, review_and_refine]
  artifacts: [candidate_work, development_evidence, revision_notes, unresolved_limits]
communication:
  recommended:
    detail: none
    wisdom: {enabled: false}
    mechanisms: []
  on_restriction: adapt_without_escalation
meetings:
  recommended: false
  max_rounds: 1
  max_total_words: 600
delegation:
  max_depth: 0
  max_children_per_agent: 0
  budget: inherited
decision_tools: inherit
model: inherit
---

# F · Single scientist

One scientist owns the investigation, implementation, testing, interpretation and revision.
The user may edit this scientist's persona and select a generation model. There are no
co-leaders, peer teams or delegated children in this design. The code controller still owns
accounting, scheduling, evidence boundaries and permitted tool execution.

## Persistence and sequences

The user selects low, medium or persistent effort. In fixed-pass mode the respective defaults
are 1, 3 and 6 investigative passes per sequence. A pass is one bounded agent episode, which
may use the declared decision and experiment tools before returning its result. Later passes
must audit the previous work, address a concrete weakness or examine an alternative; simply
repeating a conclusion is not improvement.

Persistent effort also supports budget mode: continue making passes until the sequence's
request allowance or time allowance is reached. For multiple sequences, the controller divides
remaining allowances across the remaining sequences. It never creates a new budget for a
sequence, decision, retry or fallback. Transport failures do not authorize automatic retries.

The user chooses a positive number of sequences. They run in order, using the same scientist
and continuing the same working context by default. Completed passes, receipts and failures
remain recorded. An explicit fresh-sequence context option is available for context comparisons;
it does not create independent statistical trials or erase retained evidence.

## Evidence and stopping

Use evaluator receipts when making measured claims. A self-review or semantic judgment does
not establish correctness. Retain contradictory findings and unresolved issues. When a
candidate fails, use permitted developmental evidence to revise it within the chosen effort
and budgets. Do not change lab settings, tools, budgets or confirmation rules yourself.

Fixed-pass work can stop incomplete when a shared budget is exhausted. Budget-driven sequences
can end normally at their assigned allowance, including a partially finished final episode;
such a boundary is recorded, not presented as a solved mission. Unexpected failures stop the run.

Development across all sequences precedes a single final confirmation, where supported and
budgeted. Confirmation is controller-owned and never returned to acting contexts. The user
chooses statistical methods. No persistence level implies greater correctness or a guaranteed
research improvement.

See [configuration and commands](../docs/SINGLE_SCIENTIST.md).
