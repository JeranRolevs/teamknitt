# Multiple labs and research sequences

A multi-lab study is an optional layer above individual labs. Each lab uses a study
variant, so labs can repeat the same design or use different designs. Every lab
keeps its own actor histories, outputs, development receipts and confirmation.
The user chooses labs, communication, meetings, budgets and sequence count.
There is no automatic lab selection, redesign, ranking or extra sequence.

## Start and inspect

```sh
teamknitt engine init my-labs --template multi-lab
cd my-labs
python3 engine.py prepare --multi-lab
python3 engine.py visualize --multi-lab
```

Open the printed local URL. The process view shows lab research, presentations,
discussion, exchange boundaries and final confirmation. The runtime observer locates
active actors and requests within their lab using activity metadata only.
Preparation and visualization make no model calls and need no credentials.

Edit study.yaml to configure a generation service and replace AWAITING_USER_PROBLEM
in mission/problem.md. Then explicitly run:

```sh
python3 engine.py run --multi-lab --sequences 2
```

The sequence override enters the saved configuration identity without rewriting
study.yaml. Choose either a single-lab `--variant` or `--multi-lab`.

## Choose the labs

The starter supplies silos and scientist variants. This section selects them as
two separate labs:

```yaml
multi_lab:
  labs:
    - id: mesa
      variant: silos
    - id: arroyo
      variant: scientist
  sequences: 2
  context_policy: continue
  communication:
    profile: wisdom_only
    wisdom: true
    max_read_words: 700
  meeting:
    kind: symposium
    discussion_rounds: 1
  budget:
    max_llm_calls: 64
    max_wall_seconds: 1200
  resources:
    max_active_labs: 2
    max_llm_requests: 2
    max_experiments: 2
```

Add entries with unique lab IDs to add labs (2–32 labs). Reusing a variant creates
another lab with the same design/settings and separate state. Each variant chooses
its design, personas, internal communication, statistics, decisions, persistence and
budget. Generation uses the study's explicitly configured model. Optional decision
endpoints retain their per-variant selection and authentication.

Keep a scientist variant's inner single_scientist.sequences at 1; multi_lab.sequences
controls repetitions of the entire collection (1–1000). The scientist's persistence
still chooses passes inside each research sequence. Persistent budget effort gets
a bounded share of remaining lab requests, reserving minimum meeting requests and
future sequences. Allowances are never replenished.

## Inter-lab communication

Internal agent communication and inter-lab communication are separate settings.
All labs finish research before a meeting or new cross-lab exposure begins. Every
stage reads a frozen prior snapshot, independent of completion order or concurrency.

| Profile | Material exported to other labs |
|---|---|
| none, wisdom false | No research content, including at meetings |
| low | Reported dead ends backed by valid development receipts; no text-only proposals |
| intermediate | Compact output summaries |
| high | Summaries, findings and proposed candidate output |
| wisdom_only | Conditional lessons, conditions and limits; no summary or candidate fields |

wisdom true adds that channel to a detail profile. wisdom_only requires true.
max_read_words bounds all channels in each recipient view across all peer labs.
It bounds each delivery, rather than deleting already admitted context. Structured
filtering restricts fields; it does not formally prove that generated prose contains
no detailed recipe or identification.

The inter-lab setting is a lab-wide export permission at the sequence/meeting
boundary. It also lets the representative read that lab's export for a presentation.
It does not change agent-to-agent sharing during research. An exported finding
remains its originating lab's report, rather than independent recipient validation.

## Conference or symposium

- **none:** no meeting calls; permitted research exports can still inform the next sequence.
- **conference:** one presentation per lab, then publication of permitted presentations.
  Set discussion_rounds to 0.
- **symposium:** presentations followed by the selected discussion rounds (1–20).
  Each round discusses the prior completed stage's material, disagreements or next questions.

The first prime persona represents its lab by default. Set representative to another
existing persona instance ID from the prepared plan to choose another speaker.
Meeting contributions accept final actions only; experiments, specialist calls and
delegation are unavailable during a meeting. Contributions consume generation
requests under existing budgets and are filtered again before another lab receives them.

With none and wisdom false, a selected meeting is operational only: no findings
or discussion are exchanged and no meeting model calls occur.

## Continue research and retain evidence

With context_policy continue, each next sequence retains the lab's own working
history and receives permitted prior exports and meeting material. sequences: 1
runs research and the chosen meeting once. To explicitly reset working contexts,
choose fresh_sequence or `--sequence-context fresh_sequence`. Histories and received
inboxes clear at the next research boundary; saved evidence remains local.

Group request and wall-time budgets cover all labs and sequences, including meetings,
specialists and fallbacks. Each lab's request and time limits also cover all of its
research sequences and meeting contributions. Request concurrency obeys both group
and endpoint/lab caps; active labs and experiments have shared caps too. Preparation
rejects budgets below minimum planned calls; additional tool steps, invalid output or
slow requests can still exhaust a chosen budget. Failures stop further sequences
without automatic retries or budget increases.

Evaluation counts and protected reserves remain per lab. Qualified research workspaces
can add multi_lab entries referencing their variants. All research and meetings finish
before any protected confirmation opens; confirmation never returns to agents or a
later research sequence. Labs sharing missions, models or private evaluation panels
do not become independent replications merely by using different IDs.

Group trials store plan.json, summary.json and activity metadata. labs/<id>/ holds
each lab's evidence, exchanges/ holds admitted recipient views, and meetings/ holds
filtered proceedings. These generated records remain local and ignored. Comparison
reports record group settings and usage without an automatic winner or pooled
scientific-quality score.
