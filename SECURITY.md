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
cognition, synchrony, fractals, attractors or goal achievement. The unchanged Labtune license
eligibility is not broadened by support for generic tasks or brainstorming.
