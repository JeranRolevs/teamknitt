# Execution boundaries

Planning and workspace creation do not execute candidate code or call a model.
Text workflows call the configured provider only when explicitly run.

The memory example uses a trusted supervisor and a separate untrusted policy interpreter
under macOS sandbox-exec. Policy code receives causal observations and declared bounded state;
private seeds, labels, future inputs and provider credentials remain outside that process.
AST checks enforce the API; the OS sandbox is the execution boundary. Qualification must pass
on the actual machine. Unsupported platforms fail closed rather than running candidates
without the sandbox. Do not replace that failure with an unsandboxed execution path.

Numeric-state accounting and process RSS are different measures. CPU/time bounds and RSS
monitoring supplement the strict retained-state limit. Full multi-tenant isolation, arbitrary
unrestricted Python execution and Linux/Windows policy sandboxes are not implemented.

Keep .env, private_splits.json, generated trials and results out of Git. Trial prompts and
outputs may contain user research details; inspect them before intentionally sharing.
Report issues to the repository owner through the channel they provide; no contact address
or vulnerability-reporting endpoint is assumed here.


## teamknitt task teams and monitoring

The schema-3 user controls choose a task purpose, member count, topology and sharing; model,
tool, statistical, delegation and budget limits stay explicit in the engine settings. Routes
filter both native peer views and generated representation exposure. Custom links are directed;
shared artifacts cannot bypass them. Bounded sources use workspace-relative paths; credential,
private runtime and seed-panel locations are rejected. Generated notes are append-only records,
not arbitrary file writes or executable code. Partial exposure and version-specific receipts
do not prove understanding, agreement or task correctness.

Live model execution requires both --live and explicit approval of the resolved request cap.
The default creates text contributions only, not unrestricted external actions. Low generic-task
blockers remain unverified reports; the engine's measured research receipts are not fabricated.
Larger teams, drafts and observation tools never select another model or raise a budget.

The loopback server permits only page/state metadata and non-mutating draft previews. It has
no configuration-write, arbitrary-file, model-call or run-start route. Applying a CLI draft
requires an acknowledged reset, private backup and the shared engine lock; task text and
provider/budget settings are unchanged. Offline snapshots escape embedded data, create new
private files only and cannot use workspace APIs. This is not a multi-user authenticated service.

Raw trials, deliverables, source/generated text, keys, config backups and research records are
private ignored data. Metadata itself can be sensitive. Polling shows saved checkpoints and
producer heartbeat; stale telemetry is not proof of continued execution. No automatic recovery
or cryptographic audit guarantee is claimed. Observation dimensions do not certify latent
cognition, synchrony, fractals, attractors or goal achievement. The unchanged teamknitt license
eligibility is not broadened by support for generic tasks or brainstorming.

The six focused views in two explanatory groups are presentation-only. The optional CLI `--probe-run` reads one
explicitly selected saved protocol and exports allowlisted summary metadata, never messages,
private facts or episodes. The browser has no probe-path selector or evaluation endpoint.
Attached evidence remains a separate context, not a capability claim about the current
roster. Unknown measurements and fixture-only values are labelled accordingly. These
summaries can still be sensitive; keep them and snapshots private. Delayed monitor polls
cannot replace a newer user draft or record selection.

## Explicit operator control, not a new browser execution API

`teamknitt intervene RUN --action ...` previews by default. Only explicit CLI `--apply` queues
one run/configuration-bound pause, resume, stop or feedback request. Requests are bounded,
private regular files; feedback input is bounded workspace-relative UTF-8 .md/.txt, excluding
credential/runtime paths and symlinks. Unknown privilege/configuration fields and foreign-run
bindings are rejected. Queueing performs no provider calls or model/configuration writes.

The runtime acknowledges at the next dependency-wave boundary. Already-approved current-wave
work may finish. Pause holds the shared lock while the original wall deadline elapses; resume
never resets counters or limits. Stop is terminal, preserves partial output and cannot use
completed-study confirmation. Feedback context is not an engine-permission grant; delegated
children acquire no new source access. Requests at run end may remain unapplied with receipts.

Audit metadata excludes message text. Frame assembly does not prove provider delivery or
understanding; receipts do not establish causal improvement. The queue assumes a trusted local
operator and OS filesystem permissions, not multi-user authorization or tamper-proof auditing.
A terminated/stale producer cannot acknowledge requests; no automatic retry/restart/recovery
is implied. The HTTP API remains read-only and never queues an intervention or schedules a
condition. Main-run controls do not implicitly govern advanced engine or multi-lab execution.

## Multiple teams and external style references

The collection compiler binds every team to one shared task, independent native config/model
settings, explicit export member and a bounded common request/time allowance. Inter-team data
is only designated-member output along configured directed routes from completed prior waves;
peer text remains untrusted. No raw source/style file or private artifact export is automatic.
Previously exposed information is not erased; model-generated relays are not end-to-end secrecy.

External URLs are metadata references only: no network fetch, foreign prompt/configuration
conversion, plugin load or CLI delegation occurs during setup, views or execution. Local style
text requires an explicit user-authorship attestation, safe bounded workspace path and immutable
source hash. This is not automatic provenance verification or permission to relabel copied
foreign skills. Style text and peer messages grant no tools, sources, models or budgets.

All-team limits and per-team limits apply simultaneously. Native pause/resume does not renew
any allowance; connected-component barriers obey the original shared deadline. Stopped/failed
teams produce no new export. Config application/cloning is draft-first, lock-protected, backed
up privately and guarded against concurrent edits. Historical configs/results are not removed.
Collection feedback resolves a fixed, verified parent-run/team directory chain, not a
caller-supplied filesystem root. The HTTP layer remains metadata/draft-only, with no arbitrary
file paths, remote-style loader, queue-write or execution route. Snapshots are offline/private.
