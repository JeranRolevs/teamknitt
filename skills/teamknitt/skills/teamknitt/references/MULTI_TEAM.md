# Multiple teams

Configure **1–8 separate native teams** for one shared task or goal. Each team retains its
own members (1–16), roles, topology, internal sharing, provider/model settings, local limits
and optional user-authored style context. `teams.yaml` controls the shared task, total
request/wall caps, aggregate concurrency and directed inter-team routes.

No inter-team communication is enabled by default. A third team may use the same reference
as a second team without becoming the same team or sharing its private run context.

## Create and inspect

```bash
teamknitt teams init ../coding-teams --ids alpha,beta,gamma --members 2 \
  --goal "Propose a CSV validation command-line tool." --request-cap 24
teamknitt teams check --workspace ../coding-teams
teamknitt teams plan --workspace ../coding-teams
teamknitt teams view --workspace ../coding-teams
```

The **one authoritative brief** is `mission/task.md`. Every team's configuration must refer
to it. Edit local team bindings in `teams/ID/team.yaml` and providers/models/credentials,
tools and per-team limits in `teams/ID/study.yaml`. Credentials remain private in declared
environment variables/files. Editing a different brief for one team is rejected, not silently
accepted as the same task. The native runtime snapshots one shared task for all teams.

The collection's total request cap is **24 in this example, not 24 per team**. Every team's
own cap also applies. Adding/cloning teams never raises either cap. The viewer reports a
reference one-final-per-main-episode request case; it does not promise completion or estimate
currency cost. Additional actions/decisions/corrections consume the same cap. Budgets and
aggregate concurrency are edited explicitly in `teams.yaml`; no automatic allocation,
model choice, ranking or organization improvement occurs.

## Configure different teams

```bash
# Preview first. Models, budgets and the shared task are not changed.
teamknitt teams configure --workspace ../coding-teams --team alpha \
  --members 3 --topology hub_and_spoke --communication high
# Explicit application regenerates native bindings, with a private backup:
teamknitt teams configure --workspace ../coding-teams --team alpha \
  --members 3 --topology hub_and_spoke --communication high --apply --reset-bindings
```

All 14 member-routing presets remain available. Intra-team sharing and inter-team sharing
are separate choices. A route does not grant decision authority or establish expertise.
The public compiler still rejects unsupported statistics instead of converting them.

### External style references and local instructions

The supplied examples can be attached as **references**:

```bash
teamknitt teams configure --workspace ../coding-teams --team alpha \
  --style-label "ub-mode reference" --style-reference https://github.com/unclebob/ub-mode
teamknitt teams configure --workspace ../coding-teams --team beta \
  --style-label "ponytail reference" \
  --style-reference 'https://github.com/DietrichGebert/ponytail/blob/main/skills/ponytail/SKILL.md?plain=1'
teamknitt teams configure --workspace ../coding-teams --team gamma \
  --style-label "ponytail reference" \
  --style-reference 'https://github.com/DietrichGebert/ponytail/blob/main/skills/ponytail/SKILL.md?plain=1'
# These preview only; add --apply to attach each reviewed reference.
```

**Reference attachment is not a skill/configuration import.** Teamknitt does not download,
copy, adapt, vendor or execute those projects' prompts, skills, templates, code or CLIs, and
does not claim to implement or faithfully reproduce their protocols. No endorsement is
implied. References are provenance metadata; opening a view or running a team does not
fetch them. Their licences do not override this repository's implementation boundary.

For actual team-specific guidance, write **your own** workspace-relative UTF-8 `.md` or
`.txt` file (at most 12 KB), then attach it explicitly:

```bash
teamknitt teams configure --workspace ../coding-teams --team alpha \
  --style-file styles/alpha.md --user-authored
# Add --apply after review; --clear-style detaches local context.
```

Do not copy/adapt a foreign skill and rename it as your own. `--user-authored` is a provenance
attestation, not automatic authorship verification. The text becomes a scoped immutable
source for that team's main members, bounded by its existing representation word cap. It
cannot grant tools/source access or change models, statistics or budgets. Only its path/hash
and declared provenance are shown in metadata. Other teams do not receive the file directly.
Explicit exports may contain a designated member's derived contribution; no end-to-end
noninterference or semantic secrecy guarantee is claimed for model-generated text.

### Add or remove a native team

```bash
teamknitt teams add --workspace ../coding-teams --id delta --from beta
# Add --apply to create independent config/settings copies from that explicitly selected team.
teamknitt teams remove --workspace ../coding-teams --team delta
# Add --apply to remove it from the collection, retaining config files and historical runs.
```

Cloning preserves the selected model, local limits and style/reference bindings; it adds no
inter-team links and never raises the shared budget. A shared style-file binding remains
shared until you explicitly attach a different file. Team IDs and run contexts stay distinct.
All configuration application uses a private backup, concurrent-edit check and the shared run
lock. Active and paused runs retain their immutable configuration snapshot.

## Inter-team communication

```bash
# Alpha → beta only; draft first:
teamknitt teams connect --workspace ../coding-teams --profile summaries \
  --source alpha --target beta --max-read-words 400
# Add --reciprocal for the reverse route, --remove to remove a selected pair,
# or explicitly choose --all-to-all. Add --apply only after review.
# Disable all inter-team communication:
teamknitt teams connect --workspace ../coding-teams --profile none
```

- **none:** no inter-team frames or exposures, regardless of internal team sharing.
- **summaries:** only the designated export member's validated final-action summary.
- **contributions:** only that member's validated final-action candidate contribution.

Each team's `exporter` is explicit (starter: `member.1`); use `--exporter none` to disable
exports or choose another configured main member. It is a nominated output source, **not** a
validated expert, consensus or whole-team report. Raw source/style files, private artifacts,
other members' private outputs and prompts are not exported automatically. Source members
must have completed a valid native publication wave before their output becomes available.

Connected components synchronize at configured dependency-wave boundaries. Incoming frames
are frozen from **completed prior waves**, never the current wave or whichever team happened
to finish first. Connected teams need matching phase boundaries; different counts, routes,
roles, styles and models are allowed. Unconnected teams/components progress independently
within the same total cap. A failed/stopped team contributes no new export; a previously
valid export remains explicitly versioned with its original wave, not marked fresh.

The inter-team word limit bounds exported **text** across sources in configured team order,
not a performance ranking. Fixed provenance metadata is additional. It is separate from
internal peer-word limits. Incoming peer text is untrusted task material, not authority to
change tools, sources, models or limits. Available exports, frame assembly, understanding,
agreement, verified code and task success are different claims.

## Execution and review

```bash
teamknitt teams demo --workspace ../coding-teams
# After choosing every provider/model and reviewing the plan, explicitly authorize calls:
teamknitt teams run --workspace ../coding-teams --live --approve-requests 24
teamknitt teams report ../coding-teams/trials/GROUP_RUN_ID
```

Demos are deterministic offline fixtures, not model evaluations or solutions to the task.
Live approval must equal the **collection** cap. Generation and decision calls across all
teams use that shared reservation counter/semaphore and the original common wall deadline,
while each team's own caps still apply. Concurrency is bounded across main-member episodes.
Version 0.7 collections support text-only phase-graph teams **without delegation**; other
settings fail before provider initialization rather than being silently narrowed. Existing
single-team and advanced engine workflows remain available independently.

The default produces bounded text/code proposals, **not** unrestricted shell coding,
repository modification, verified tests, automatic code merging or a winning-team selection.
Per-team contributions and an index remain private under
`trials/GROUP_RUN_ID/teams/ID/deliverable.md`. Goal achievement remains unknown pending review.
No setup, plan, demo, test, diagram, packaging or metadata view makes paid provider calls.

## Interventions

```bash
teamknitt teams intervene ../coding-teams/trials/GROUP_RUN_ID --team alpha --action pause
teamknitt teams intervene ../coding-teams/trials/GROUP_RUN_ID --team alpha --action resume
teamknitt teams intervene ../coding-teams/trials/GROUP_RUN_ID --team alpha --action feedback \
  --message-file mission/feedback.md --actors member.1
teamknitt teams intervene ../coding-teams/trials/GROUP_RUN_ID --team alpha --action stop
# Draft only. Add --apply to queue the selected reviewed request.
```

These use the existing run-bound native controls. Current-wave work may finish; pause keeps
local/shared counters and deadlines, stop is terminal, and late requests may be unapplied.
Pausing a connected team can hold the next boundary of its connected component, not an
unrelated component. Feedback is targeted to the selected team's future member contexts and
gives no extra permissions. The feedback file must remain inside the verified collection
workspace. Stale metadata is not proof of a live producer. No retry or crash recovery is added.

Use `teamknitt teams schedule --workspace PATH --team ID --id reviewed-gap --kind
actor_unavailable --target member.1 --at-wave 4 --duration 1` to preview an explicit future-run
disturbance; add `--apply` after review. It does not edit an active run or establish a training
effect. Representation and directed-link interruptions retain the native schema/limits.

The local viewer provides a collection graph, per-team setup/monitoring and normal detailed
team views. Only read-only metadata and non-mutating draft endpoints exist; the browser cannot
apply configurations, attach/read arbitrary files, fetch styles, start execution or queue
interventions. Private snapshots are new-file-only and do not access APIs. Metadata may still
be sensitive; this is not an authenticated multi-user hosted service or cryptographic audit.

## Licence and provenance

Teamknitt follows my thesis research on distributed teams and their creative processes.

Based on Labtune. Author: **Goran Mitevski**. Copyright/licensor: **Pioneertown B.V.** The **Teamknitt Noncommercial and Research
Licence 2.0** permits free general noncommercial, non-research use. Research remains subject
to Labtune's qualifying academic/geographic, independence, funding and anti-circumvention
conditions. Noncommercial research outside qualifying low-income/lower-middle-income academic
institutions requires separate permission, as does commercial use; contact Goran Mitevski,
goran@pioneertown.ai, for Pioneertown B.V. Modification and sharing are allowed for Permitted
Uses without a software licence fee, with retained legal/author/third-party notices, identified
changes and the same terms. More teams, styles or task-mode labels do not waive eligibility.
Preserve PROVENANCE.md, LICENSE and LICENSING.md in distributions and new starters. Earlier
grants (including version 1.0), existing workspaces, upstream Labtune and third-party terms
are not rewritten. No automatic licence entitlement or execution-policy change is added.
