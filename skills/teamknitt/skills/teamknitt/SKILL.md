---
name: teamknitt
description: Configure, check, preview, run and intervene in teams of 1–16 LLM agents with the teamknitt CLI. Use this skill whenever the user mentions teamknitt, or wants to set up a team of AI agents for a task, brainstorm, goal or research question and decide who talks to whom (topology), how much they share, and what budget they get; also for comparing several agent teams on one task, viewing a team's work as a snapshot, or pausing, stopping or giving feedback to a running team. Not for writing agent code with an SDK or framework.
---

# teamknitt

teamknitt is a command-line tool for configuring, observing and intervening in teams of 1–16
LLM agents. A person chooses the team's purpose, size, routing (who may send to whom), sharing
level, model and budget; teamknitt runs the team within those limits and records what happened.

Your job with this skill is to operate the CLI on the user's behalf: turn what they want into a
workspace, show them what it will do, and run only what they have approved.

## Principles that shape every step

teamknitt is built around explicit human choices. Keep to that, because users rely on it:

- **The user chooses; you draft.** Purpose, team size, topology, sharing, provider, model and
  budget are the user's decisions. Suggest a starting point and say why, but present it as a
  choice. The topologies are fixed routing presets, not recommendations teamknitt has computed.
- **Preview before applying.** `configure`, `intervene`, `schedule`, `teams connect`, `teams add`
  and `teams remove` only preview until you add `--apply`. Show the preview, then apply once the
  user agrees.
- **No model calls without a clear yes.** Everything except `run --live` (and
  `engine … doctor --live`) is offline and free. A live run spends the user's provider budget, so
  state the request cap and wait for their go-ahead.
- **Describe results as what they are.** A demo is a software fixture, not a model's answer. A
  finished run produced contributions for the user to review; it did not establish that the task
  is solved. teamknitt gives no team-quality score, and you should not invent one.
- **Never raise a budget or change a model on your own.** Bigger teams do not get a bigger cap.

## 1. Set up the CLI

Check first; install only if needed. Python 3.11 or newer is required.

```bash
command -v teamknitt && teamknitt --version
```

If it is missing, install it from the author's repository at the pinned commit below. This is
teamknitt 0.9.0; the pin means every user gets exactly the code this skill was tested with.

```bash
python3 --version
python3 -m venv "$HOME/.teamknitt-venv"
"$HOME/.teamknitt-venv/bin/pip" install \
  "https://github.com/JeranRolevs/teamknitt/archive/01e8e16802acbfea35f8896a3de258bc7f53fa34.zip"
"$HOME/.teamknitt-venv/bin/teamknitt" --version
```

- Tell the user in one line that you are installing teamknitt from
  github.com/JeranRolevs/teamknitt before you do it. The install also downloads two dependencies
  from PyPI (PyYAML and jsonschema).
- If the archive download is refused but `git` works, use
  `pip install "git+https://github.com/JeranRolevs/teamknitt@01e8e16802acbfea35f8896a3de258bc7f53fa34"` instead.
- If both are refused, the network is restricted. Ask the user to attach the repository as a ZIP
  (GitHub: Code → Download ZIP) and install from the unpacked folder.
- Install only from that repository at that commit. Do not substitute another source, branch or
  version on your own.
- Shell state may not carry between commands, so call the binary by its full path
  (`$HOME/.teamknitt-venv/bin/teamknitt`) wherever plain `teamknitt` is not found.

This skill's `references/` folder holds the guides. Read one when you need detail the sections
below do not cover: `references/TEAMKNITT.md` (configuration, views, interventions),
`references/MULTI_TEAM.md` (several teams), `references/PROVIDERS.md` (connecting a model
service).

## 2. Agree the team with the user

You need five things. Take what the user already said, propose the rest, and confirm in one go
rather than asking five separate questions.

| Choice | Options |
|---|---|
| Purpose | `task` · `brainstorm` · `goal` · `research` |
| Members | 1–16 |
| Topology | 13 presets or `custom` (below) |
| Sharing | `none` · `low` · `intermediate` · `high` · `wisdom_only` |
| Brief | One or two sentences now; the full text goes in `mission/task.md` |

**Topology** decides who may send information to whom:

| ID | Routing |
|---|---|
| `fully_connected` | Everyone with everyone |
| `hub_and_spoke` | Member 1 exchanges with each spoke; spokes not with each other |
| `ring` | Two-way neighbours in a closed loop |
| `chain` | Two-way neighbours, no closing loop |
| `hierarchical` | Two-way binary tree (routing only, no authority) |
| `wheel` | Hub plus a ring among the spokes |
| `grid` | Near-square grid, horizontal and vertical neighbours |
| `clustered` | Pods of up to three, fully connected inside; pod leads link the pods |
| `bipartite` | Two halves; links only across, never within |
| `directed_chain` | 1 → 2 → … → N, no replies |
| `directed_ring` | Each sends to the next; the last sends to member 1 |
| `broadcast` | Member 1 sends to all; no replies |
| `gather` | All send to member 1; nothing comes back |
| `custom` | Exactly the directed links listed in `team.yaml` |

`teamknitt topologies` prints the full catalogue.

**Sharing** limits what may travel along those routes: `none` (independent work), `low`
(reported blockers only), `intermediate` (short summaries), `high` (detailed notes),
`wisdom_only` (conditional lessons, not detailed output).

Useful ways to explain a suggestion: independent drafts for comparison → any topology with
`none`; open idea exchange → `fully_connected` or `ring` with `high`; one coordinator →
`hub_and_spoke`; a pipeline where each builds on the last → `directed_chain`; sub-groups →
`clustered`. These are starting points for the user to accept or change, not findings.

## 3. Create the workspace and check it

```bash
teamknitt init ./my-team --purpose brainstorm --members 4 --topology ring \
  --communication high --goal "Brainstorm welcoming workshop formats."
teamknitt check --workspace ./my-team
teamknitt plan  --workspace ./my-team
```

`init` refuses to overwrite an existing folder. All commands print JSON.

Then put the user's material in place:

- `mission/task.md` — the brief the team works on. Write the user's full request here.
- `mission/context.md` — background, constraints, source notes. Replace the starter text.
- `team.yaml` — purpose, topology, members, sharing, roles and work bindings. It is written as
  JSON; edit it carefully and run `check` afterwards.
- `study.yaml` — provider, model, tools and budgets.

From the `plan` output, tell the user in plain words: the members and routing, the number of
waves, and `provider_request_cap` (the most model requests a live run may make; it is a count,
not a cost estimate).

## 4. Show the team

A snapshot is a single private HTML file that opens offline:

```bash
teamknitt view --workspace ./my-team --output ./my-team-view.html
```

`--output` never overwrites, so use a new file name each time. Where you can deliver files to
the user (chat or cloud sessions), send them the snapshot. On the user's own machine you can
instead start the local viewer, which keeps running until stopped:

```bash
teamknitt view --workspace ./my-team --port 8765    # serves http://127.0.0.1:8765
```

Run that in the background and give the user the address. The viewer only displays; it cannot
change the configuration or start a run.

Focused research views: add `--group non_system|system` and `--section` with one of
`collaborative_intelligence`, `shared_models`, `distributed_problem_solving`,
`transactive_memory`, `team_dynamics`, `interaction_coordination`. `teamknitt views` and
`teamknitt theory` explain them. Switching views changes the presentation only.

## 5. Change the configuration

```bash
# Preview: nothing is written.
teamknitt configure --workspace ./my-team --members 6 --topology clustered
# After the user agrees:
teamknitt configure --workspace ./my-team --members 6 --topology clustered --apply --reset-bindings
```

Applying backs up the previous configuration and regenerates the starter roles and work
bindings. If the user has hand-edited roles or bindings in `team.yaml`, tell them a reset would
replace those, and edit `team.yaml` directly instead. Run `check` and `plan` again after any
change. Changing team size does not change models or budgets.

## 6. Demonstrate offline

```bash
teamknitt demo --workspace ./my-team --policy connected     # or: fragmented
```

This walks the configured team through its waves with built-in placeholder text and writes a
record under `trials/RUN_ID/`. It is useful for showing how information would flow and what the
records look like. Say plainly that the text is a fixture and no model was involved.

## 7. Run with real models

A live run needs three things from the user, set in the workspace:

1. In `study.yaml` under `provider`: `base_url` and `model` for a chat-completions-compatible
   service of their choosing. The starter values (`provider.example.invalid`, `YOUR_MODEL_ID`)
   deliberately block live runs.
2. The key in the workspace's `.env` file as `TEAMKNITT_API_KEY=…` (copy `.env.example`). The
   user should place it there themselves. Do not ask them to paste a key into the conversation,
   and never write a key into `study.yaml` or any file you send back.
3. Their approval of the request cap that `plan` reports.

```bash
teamknitt plan --workspace ./my-team                      # read provider_request_cap, e.g. 24
teamknitt run  --workspace ./my-team --live --approve-requests 24
```

`--approve-requests` must equal the cap exactly. To change the cap the user edits
`base_overrides.budget.max_llm_calls` in `study.yaml`; that is their call. The run blocks until
it finishes, so on a local machine start it in the background if the user may want to intervene.

**In a chat or cloud sandbox** the provider usually cannot be reached and the user's key does not
belong there. Prepare and check everything, then hand over: zip the workspace, send it, and give
the user the two commands above to run on their own machine, after installing teamknitt there
with the same pinned `pip install` line as in section 1.

## 8. Read the results

Each run writes `trials/RUN_ID/`:

```bash
cat ./my-team/trials/RUN_ID/deliverable.md               # the members' contributions
teamknitt view ./my-team/trials/RUN_ID --workspace ./my-team --output ./run-view.html
(cd ./my-team && teamknitt report trials/RUN_ID)         # process metadata as JSON
```

Summarise the deliverable for the user and point out open questions and disagreements between
members. Report process facts (who contributed, which handoffs happened, requests used). Leave
the judgement of whether the goal was met to the user.

## 9. Intervene in a run

Interventions apply to a run that is still going (running or paused). A finished or stopped run
answers `This run is terminal`. Run these from inside the workspace folder. Each previews until
`--apply` is added, and takes effect at the next wave boundary, not instantly.

```bash
teamknitt intervene trials/RUN_ID --action feedback --message-file mission/feedback.md --actors member.1
teamknitt intervene trials/RUN_ID --action pause
teamknitt intervene trials/RUN_ID --action resume
teamknitt intervene trials/RUN_ID --action stop
```

Feedback is a private note (a `.md` or `.txt` file inside the workspace, at most 12 KB) for the
named members, or all members if `--actors` is omitted. Pausing does not stop the wall-time
limit from counting down. Stopping is final and keeps partial work.

To plan a disturbance for a future run (a member, a source or a link unavailable for some waves):

```bash
teamknitt schedule --workspace . --id member-gap --kind actor_unavailable \
  --target member.1 --at-wave 4 --duration 1
# other kinds: representation_unavailable (target: a source ID), link_dropout (target: 'member.1->member.2')
```

## 10. Several teams on one task

Up to 8 separately configured teams can work on the same brief under one shared request cap.
They do not communicate unless a route is added, and no winner is picked automatically.

```bash
teamknitt teams init ./teams --ids alpha,beta,gamma --members 2 \
  --goal "Propose a CSV validation command-line tool." --request-cap 24
teamknitt teams check --workspace ./teams
teamknitt teams plan  --workspace ./teams
teamknitt teams view  --workspace ./teams --output ./teams-view.html
teamknitt teams configure --workspace ./teams --team alpha --members 3 --topology hub_and_spoke
teamknitt teams connect   --workspace ./teams --profile summaries --source alpha --target beta
```

The cap is for all teams together, not per team. `teams configure` and `teams connect` preview
until `--apply` (`configure` also needs `--reset-bindings`). The shared brief is the collection's
`mission/task.md`; per-team settings live in `teams/ID/team.yaml` and `teams/ID/study.yaml`.
`teams demo`, `teams run`, `teams report` and `teams intervene` mirror the single-team commands.
Read `references/MULTI_TEAM.md` before using style references, cloning or exporters.

## When something fails

- Errors start with `teamknitt error:` and say what to fix. Relay them plainly.
- `run requires --live and --approve-requests` — a live run was not explicitly authorised; use
  `demo` for an offline walk-through.
- `Set your provider base_url and model` — `study.yaml` still has the starter placeholders.
- `File exists` from `view --output` — choose a new file name.
- For anything unfamiliar, run the command with `--help`; `teamknitt engine --help` and
  `teamknitt probes --help` cover advanced research workflows this skill does not walk through.

## Licence

Using teamknitt through this skill in Claude is covered by the Teamknitt Skill Licence 1.0
(`skills/teamknitt/LICENSE` in the teamknitt repository), which permits use by anyone for any
purpose. At this stage the licence covers Claude only and does not allow changing the skill: if
a user asks you to edit, port or rework this skill, tell them that needs the licensor's written
permission. Using the teamknitt code apart from the skill stays under the Teamknitt Noncommercial
and Research Licence 2.0. Keep the `LICENSE`, `LICENSING.md` and `PROVENANCE.md` files that each
workspace contains, and do not copy teamknitt code into other projects. If a user asks whether
a particular use is allowed, point them to those files and to the licensor rather than deciding
for them. Author: Goran Mitevski. Licensor: Pioneertown B.V.
