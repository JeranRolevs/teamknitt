# Research and configuration record templates

These are twelve marked examples, not evidence of executed research. All shipped JSON records
have `template: true`, placeholder references, and an example timestamp. The schema validates
shape; a future store/runtime checks source existence, authority, permissions, and actual results.

| Record | Purpose |
|---|---|
| `mission` | Objective, comparator, measurements, constraints, scope, and confirmation |
| `configuration_snapshot` | Audit-only fingerprint of the user's selected settings and input bindings |
| `configuration_change` | User request, before/after snapshot references, effective boundary, prior exposure |
| `research_event` | Observable prediction, action, result, revision, claim, or sharing read |
| `experiment` | Identified candidate/inputs and proposed/executed investigation status |
| `evaluation_receipt` | Evaluator identity, measurements, validity/failure, evidence, resource use, and statistical approach/status/protocol/results |
| `memory_entry` | Detailed scoped finding with support, contradictions, conditions, and revisions |
| `decision_request` | Compatible question, caller-visible context, answer space, and budget references |
| `decision_result` | Typed answer/abstention/failure, backend, support, fallback, and usage |
| `sharing_view` | Recipient-filtered files, source lineage, content identity, and exposure |
| `asset` | Usable output with confirmation, scope, recipe, and recheck conditions |
| `knowledge_snapshot` | Declared starting knowledge and actual prior exposure |

Configuration snapshots do not freeze editable settings. No lab-version acceptance or automatic
improvement records exist. The future runtime records when a user's change takes effect and
retains earlier exposure history. An independent comparison can use fresh contexts if the user
chooses. See [the architecture](https://github.com/JeranRolevs/teamknitt/blob/main/ARCHITECTURE.md) and [schema](https://github.com/JeranRolevs/teamknitt/blob/main/src/teamknitt/engine/schemas/records.schema.json).
