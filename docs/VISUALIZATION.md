# Visualize a chosen lab and observe its work

The optional lab observatory is a local web page driven by two read-only agents:

- **Setup visualizer** maps the resolved design, persona instances, dependency graph,
  sharing profile, models, delegation limits, statistics and budgets.
- **Runtime observer** follows activity records and highlights the workflow nodes and
  actors performing model requests, decisions, evaluations, child work and confirmation.

Both agents are deterministic local services. They make no model calls and need no API key.
They cannot start research, send messages to researchers, change lab settings or schedule work.
The viewer is outside research contexts and does not create a peer communication channel.

## Process-control display

The display uses a neutral process-control layout. Execution, data source, last telemetry
time in UTC and evidence status occupy fixed positions above the process diagram. Request
counts show their configured concurrency and budget limits; token receipts show exact counts.
Actor rows stay in the same positions across workflow stages. The Team view and selected-object
panel provide detail without removing the process context.

Ordinary and completed work are gray. Blue identifies active computation, amber identifies
uncertain telemetry, and red identifies failed or interrupted work. Each node also has a
symbol and explicit state text. There are no blinking indicators or animated transitions.
Status notes explain observed exceptions and a useful next action. Recovered errors stay in
the journal rather than becoming invented active alarms.

An ended workflow is labeled **ENDED**, with evidence status shown independently. For example,
a text-only run remains **NOT EVALUATED** even when every acting episode finished. Snapshots,
paused views and missing telemetry are explicitly distinguished from current observation.

[Display design notes](VISUALIZATION_DESIGN.md) record the rationale and reference guidance.

The yellow (`#FFDA00`) teamknitt wordmark uses Noir Pro Medium (weight 500) when installed on
the viewing computer. Noir Medium and system sans-serif fonts provide fallbacks. Font loading
stays local, including in exported snapshots.

For [design F](SINGLE_SCIENTIST.md), the setup panel also records persistence, fixed-pass or
budget-driven effort, sequence count and context policy. The execution field follows current
sequence/pass progress. The diagram keeps one scientist row and shows ordered pass boundaries
or one budget loop per sequence; it does not imply additional scientists were launched.

## Open the selected design

From a checkout, after installing teamknitt:

```bash
teamknitt engine --project . visualize
```

Open the printed `http://127.0.0.1:8765/.../` URL. Leave the command running while viewing;
Ctrl-C stops the server. It binds only to loopback, with a fresh private URL for each session.
Use `--port 0` to choose an available port or `--port 8766` if the default is occupied.

Select another design or communication/statistical choice for a structural preview:

```bash
teamknitt engine --project . visualize \
  --design lab_designs/C-complementary-co-leaders.md \
  --profile wisdom_only --statistics frequentist
```

Previewing does not write these choices into the configuration. The diagram reflects the
resolved file and explicit overrides. Workflow arrows show dependencies; they do not grant
access to peer data. The Team tab groups configured roles and shows observed child delegation;
it does not invent team reporting relationships absent from the plan.

## Observe a study variant

In an initialized workspace:

```bash
python3 engine.py visualize --variant single
# For the memory example instead:
python3 engine.py visualize --variant memory-single
```

The equivalent generic command is:

```bash
teamknitt engine --project ../my-lab visualize --workspace ../my-lab --variant single
```

The page begins with the chosen setup. In another terminal, explicitly start a run using the
normal `engine.py run --variant ...` command. Research calls still consume the budgets selected
in that workspace. Opening the viewer does not launch or qualify a research run.

“Latest matching run” attaches only to a trial with the same configuration snapshot identity.
Code or configuration changes produce a different identity. The run selector also lets you
inspect saved trials; those views always use the trial's recorded plan. Setup-only view and
pausing updates are available. Choosing a saved trial from the command line is explicit:

```bash
python3 engine.py visualize --trial YOUR_SAVED_TRIAL_ID
```

The map distinguishes planned, ready, active, completed, deferred, skipped, failed and unknown
work. Multiple simultaneous requests remain visible. A parent waiting for a child is marked
waiting in the Team map. Confirmation appears after all acting phases, separately from the
bounded runner's deferred verification placeholders. A completed step is an execution signal,
not proof of scientific validity or a quality judgment.

Active highlights follow observed runtime activity, not hardware sampling. The page shows
request time, token receipts and evaluation attempts; it does not claim remote CPU/GPU usage,
provider billing or confirmed research improvements. Error events can include both a failed
request and the enclosing failed operation. Missing usage receipts do not imply zero cost.

## Save an offline page

```bash
teamknitt engine --project ../my-lab visualize --workspace ../my-lab \
  --variant single --output /tmp/teamknitt-process.html
```

Or click **Save snapshot** in the live page. Each saved page contains its data, CSS and
JavaScript, with no CDN or external assets. It opens offline and retains inspection, zoom and
map switching. It is labeled as a snapshot and does not show stale observations as live work.
The CLI refuses to overwrite an existing output file. Keep exports with local results if
they include private run metadata; nothing is hosted or published by teamknitt.

## Runtime integration and data boundary

The generic runner appends a small `activity.jsonl` alongside its full private `events.jsonl`.
Activity records contain only an allowlist: sequence/time, workflow node, actor/team/episode
identities, event kind, request or activity identity, category, provider/model route, status,
elapsed time and token counts. Prompts, model answers, shadow judgments, candidate source,
research measurements, problem text, errors with free text and artifact paths are excluded.
The observer never opens `.env`, private seeds, actor outputs or evaluator artifacts.

New runs also update `activity-heartbeat.json` every two seconds. A heartbeat older than
15 seconds, a missing heartbeat or a disconnected/paused viewer removes live computation
indicators. A terminal summary takes precedence. Old trials can be replayed from sanitized
events, but their activity is marked unknown when no liveness signal exists. The observer
retries incomplete JSON lines and resets its cursor if the journal is truncated or replaced.
If the observer is still reading a backlog, the page marks activity as catching up rather
than presenting older requests as current computation.

For another runtime, supply the same resolved `plan.json` and summary convention, emit the
following metadata through `teamknitt.visualization.activity_metadata`, and update the heartbeat:

| Signal | Required identity | Meaning |
|---|---|---|
| `phase_started`, `phase_completed` | `node` | Workflow execution boundaries |
| `episode_started`, `episode_finished` | `node`, `actor: {id, team, episode}` | Actor execution; final `status` is completed/failed/cancelled |
| `provider_request`, `provider_response`, `provider_error` | `request_id`, `node`, `actor` | Correlated remote work; responses may supply token `usage` |
| `activity_started`, `activity_finished` | `activity_id`, `node`, `actor`, `category` | Local evaluation, decisions, delegation or confirmation |
| `domain_step_pending`, `operational_coordination` | `node` | Deferred or operational work without fabricated computation |

This is an observer interface; it grants no execution capability. The local HTTP server exposes
only the rendered page and filtered state, with no arbitrary filesystem routes or write API.
The viewer ships in the wheel and works on platforms where teamknitt's planning works; a domain
adapter's candidate-execution restrictions still apply to that domain's research runs.
