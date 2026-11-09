# Lab process monitor: display design

The monitor supports four questions: which configuration is being observed, where work is
occurring, whether the observation is current, and which conditions need investigation.
The user's requested direction is a restrained process-control module, grounded in cognitive
ergonomics. The implementation remains a local, read-only teamknitt observer.

## Display principles

Group information by task, keep labels and actor positions stable, use legible body text,
and pair color with words and symbols. Execution status, freshness and evidence status are
separate observations. These are teamknitt display choices, not a claim of conformance to a
third-party control-room standard.

## Information order

1. Configuration and run selection identify the object under observation.
2. Execution state, source mode, last telemetry and evidence status remain visible together.
3. Observed request counts sit beside their configured limits. Receipt totals use exact digits.
4. Status notes identify an observed problem and suggest an investigation or viewer action.
5. The process overview preserves actor rows across phases and uses orthogonal dependency lines.
6. Selected-object details, open operations and the event journal support closer inspection.

The active-request limit is a configured concurrency bound. Request-budget usage counts
observed dispatched requests. Neither represents measured CPU/GPU utilization. Completed
execution and evidence validation use separate fields; an ended text workflow does not
become a successful scientific evaluation.

## State coding

| Condition | Treatment | Text / symbol |
|---|---|---|
| Planned or ready | Neutral outline | PLANNED / READY, open square |
| Active computation | Restrained blue border and fill | ACTIVE, triangle |
| Completed execution | Neutral gray fill | DONE, check mark |
| Waiting for a child | Neutral outline | WAITING, pause symbol |
| Deferred / bypassed | Gray dashed outline | DEFERRED / BYPASSED, dash |
| Previously active in a frozen view | Gray dashed outline | RECORDED ACTIVE, tilde |
| Unknown activity | Amber border and pale fill | UNKNOWN, question mark |
| Failed or interrupted | Red border and pale fill | FAILED / INTERRUPTED, exclamation |
| Selected object | Black dashed outer outline | Detail panel and keyboard focus |

Normal operation has no decorative success color. Color is paired with words and symbols.
The page uses square modules, quiet warm-neutral surfaces, tabular digits for measurements, and
consistent UTC timestamps. It uses no animation, glowing indicators, gradient fills or
background patterns. Controls are limited to observation: selecting a record or view,
changing diagram scale, pausing refresh and saving an HTML snapshot.

## Stability and interpretation

Unchanged diagrams and detail fields are retained across polls. Actor lanes and diagram
geometry remain stable as states change. Keyboard focus, a manual zoom choice and journal
scroll position are preserved. Mobile layouts keep the state board above the horizontally
scrollable process display.

The connection indicator describes the viewer connection. It is separate from the runner's
heartbeat. A connected viewer may still show stale runner telemetry. A snapshot is identified
as a recorded observation; its active symbols cannot be mistaken for live work. A missing or
unrecognized evidence status is reported as unavailable, rather than inferred from completion.

These choices are checked with offline state fixtures, real saved-run metadata and browser
inspection at desktop and mobile widths. No provider calls are needed to change or inspect
the visual design.

## Subtle western detailing

teamknitt's display takes a small cue from survey-office instruments and printed field ledgers:
warm ivory surfaces, walnut text, muted brass rules, a slab-serif wordmark and restrained
serif section labels. Body copy, controls, state labels and measurements retain their existing
sans-serif or monospaced type. Clipped diagram corners and inset hairlines echo engraved
instrument plates. The same palette and type hierarchy appear in exported flow diagrams;
their canonical colors and display settings live in `diagrams/specs.py`.

Decorative brass is confined to framing. Active work remains blue, unknown conditions amber,
and failures red, with redundant text and symbols. No texture, animation or illustration sits
behind operational information. Static flow colors describe component categories; they do
not indicate live execution or scientific validity.
