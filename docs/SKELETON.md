# Implemented components and remaining boundaries

teamknitt now includes an opt-in bounded runner as well as the original nonexecuting structural
core. Designs, check and plan do not call models. init creates an independent workspace from
wheel resources; prepare writes plans without a key.

| Component | Current behavior |
|---|---|
| config.py / planning.py | Strict YAML, schemas, six Markdown designs, phase DAGs and identities |
| persistence.py | Single scientist, low/medium/persistent effort, fixed passes or divided budget allowances |
| scaffold.py | Fresh text/memory/scientist workspaces, explicit decision-backend choice, private memory seeds |
| study.py | Explicit provider workflows, bounded concurrency/delegation, Markdown publication, receipts |
| visualization.py / resources/visualization | Two local read-only agents, process/team maps, live metadata observation, standalone HTML snapshots |
| providers/chat.py / typed.py | Configurable generation and typed or chat decision protocols |
| memory.py | Controlled authored-source experiment API, qualification identity checks, reserved confirmation |
| research.py | Domain dispatch and a qualified workspace-evaluator bridge |
| examples/memory_retention | Independent synthetic generator, sandbox worker, evaluator, baselines and public profiles |
| contracts.py / ports.py | Wider typed interfaces for configuration, evidence, domain services and future integration |

Execution is opt-in. The memory task runs submitted source only in a separate OS-sandboxed
interpreter; the trusted supervisor owns labels, private seeds, future input and scoring.
It supports retention plus bounded auxiliary state, not arbitrary unrestricted algorithms,
compression or learned prototypes. macOS native qualification must pass. General Linux and
Windows candidate sandboxes are unimplemented.

The study runner is a bounded phase workflow, not a full multi-tenant production service.
General asset integration, a reusable registry, rich playbook services, durable scheduler
recovery and live in-run reconfiguration remain design interfaces. Settings can be changed
between runs. Configuration snapshots record choices, not a lock on future choices.

The user selects lab styles, communication, models, delegation, budgets and statistical
approach. There is no automated organizational redesign, prompt-evolution or promotion loop.
Numerical analysis belongs to qualified domain adapters. Current memory evaluation reports
CP intervals and optionally explicit-prior Beta summaries; style comparisons require a
separate user-chosen analysis.

See [architecture](../ARCHITECTURE.md), [setup](GETTING_STARTED.md), and
[all graphs](../FLOWCHARTS.md). The graphs mark planned general asset handling separately
from current bounded execution. Historical plan/idea documents preserve the earlier design.
