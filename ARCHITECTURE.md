# teamknitt and its Labtune engine

## User-directed teams, not research-only lab tuning

teamknitt exposes task/brainstorm/goal purpose, member count, topology and sharing as explicit
user controls in schema-3 `team.yaml`. `builder.py` mechanically creates starter bindings only
from those choices; a draft is never applied automatically. `topology.py` defines directed
routes. `config.py` compiles the choices into a selected Labtune task-team design, leaving
provider/model, statistics, delegation, tool and budget choices in the engine's `study.yaml`.

The retained `TextStudy` scheduler is the actual execution engine, with no-op/default wave
and peer-row hooks plus fixture-client injection. teamknitt's subclass adds scoped representations,
route-filtered peer views, versioned publication, handoffs and explicit temporal reports. Its
user-task contract does not require every brief to be scientific research. Generic low-sharing
blockers are labelled member reports, not falsely relabelled as measured research failures.

Distributed team cognition is the organizing framework across people/roles, representations,
technology, work and context. `cognition.py` validates opportunities/provenance and publishes
atomically at dependency-wave barriers. Source/own and cross-member grants remain distinct;
a topology cannot be bypassed by a generated shared note. Previously seen material is not erased.

`observations.py` is an additional, optional descriptive tool informed by Gorman et al.:
local/global activity, disturbance response, exposure coupling and cross-level records.
Attractor, synchronization and fractal dimensions are explicit not-estimated states. No overall
cognition score, topology ranking, user-goal success or automatic organizational improvement
is inferred. A private `deliverable.md` preserves actual contributions for user review.

The local viewer shares Labtune's warm neutral/brass/ink aesthetic. Its GET-only draft builder
changes no files or budgets. Metadata polling follows matching execution/checkpoints without
calling models; telemetry/heartbeat and completion/goal achievement are distinguished. Applying
configuration needs explicit CLI confirmation and preserves a private backup, task text and
engine settings. The shared engine lock prevents application during execution.

Canonical flowcharts and topology geometry originate in `diagrams/specs.py`, exported by the
starter synchronizer; the installed viewer does not need the development checkout. The advanced
schema-2 research template and secondary teammate probes remain separate, not defaults.
[Configuration](docs/TEAMKNITT.md) · [Framework and sources](docs/TEAMKNITT.md#research-framework-and-observation-sources).

![teamknitt system](diagrams/13-teamknitt-system.svg)

## Original Labtune core

The optional multi-lab coordinator composes existing study variants as separate
labs with their own histories and research backends. Shared request/time and
concurrency limits cover research and meetings. Filtered cross-lab views are frozen
at sequence and meeting barriers; protected confirmation waits until every sequence
and meeting ends. See [multi-lab configuration](docs/MULTI_LAB.md).

![Labtune integrated lab](diagrams/06-integrated-lab.svg)

The user supplies a mission and chooses a Markdown lab design. Configuration resolves
personas, phases, sharing, statistics and budgets. Ready dependency waves can run concurrently;
actor contexts remain separate and child agents inherit or narrow their parent's permissions.
A phase barrier precedes peer publication. Design F instead runs one scientist's selected
passes and sequences in order, with continued context by default and one shared budget.

Generation uses a user-configured chat-completions endpoint. Optional semantic judgments use
the same generation model or a separately declared chat/typed endpoint. Shadow opinions remain
outside acting contexts. Valid answers resume the same episode, while fallbacks and failures
consume the same budget. Endpoint and model bindings enter configuration identities.

| Layer | Implemented | Limits |
|---|---|---|
| Structural core | Six designs, schemas, strict YAML, dependency graphs, configuration identities | Describes broader planned interfaces too |
| Study runner | Explicit provider calls, bounded concurrency/delegation, JSON correction, filtered sharing | Settings change between runs |
| Domain tools | Registered qualified adapters and synthetic memory-policy execution | Candidate execution requires native macOS sandbox qualification |
| Evaluator | Separate calibration, development and confirmation panels, uncertainty and costs | Synthetic finite-horizon evidence |
| Comparison | Saved metrics, denominators, failures and compute filtered by study identity | No automatic winner or style ranking |
| Asset lifecycle | Schemas and design contracts | General registry and integration are planned |

The package ships its own starter resources. Initialization generates private seed panels
locally. Trusted evaluators own labels and future inputs; candidate source runs only in a
separate sandboxed interpreter. Confirmation occurs after development and never returns to
the acting agents. [Execution boundaries](SECURITY.md).

Two local, read-only visualization agents project the exact setup and observe filtered runtime
metadata. The viewer distinguishes execution from evidence and live activity from stale or
recorded observations. It exposes no prompts, generated code, private seeds or research results.
See [visualization](docs/VISUALIZATION.md) and [current scope](docs/SKELETON.md).
