# F · Single scientist: persistence and sequences

This lab uses one scientist, without peer teams or delegated children. The same scientist
can investigate, implement, use permitted tools, review evidence and revise their own work.
Their generation model and persona remain user choices.

## Create a workspace

```bash
teamknitt engine init ../scientist-lab --template scientist
cd ../scientist-lab
python3 engine.py prepare
```

Initialization and prepare need no account and make no provider calls. Replace
`AWAITING_USER_PROBLEM` in `mission/problem.md`, set private credentials as described in the
main setup guide, and choose budgets before explicitly running work.

The template includes three variants: `scientist-low`, `scientist-medium` and
`scientist-persistent`. Fixed-pass effort has the following defaults:

| Persistence | Passes per sequence | Intended effort |
|---|---:|---|
| low | 1 | One focused investigation |
| medium | 3 | Investigation followed by review and refinement |
| persistent | 6 | Continued review, alternatives and refinement within the shared limits |

A pass is a bounded agent episode. It may require more than one model request when using
tools, fixing output format or resuming after a decision. A final action ends that pass;
it does not certify the mission solved. Higher persistence does not guarantee better results.

## One sequence or several, continuing the same context

```bash
python3 engine.py run --variant scientist-low --sequences 1
python3 engine.py run --variant scientist-medium --sequences 3
python3 engine.py run --variant scientist-persistent --sequences 2
```

These are separate explicit run choices, not a batch to execute automatically. Three medium
sequences plan nine passes, all executed in order by `scientist.1`. Context continues across
passes and sequences. They are part of one trial with one shared budget, not independent
statistical replications. Starting another command creates another trial; durable resume
across commands is not implemented.

The controls can also be recorded in `study.yaml` under `base_overrides`:

```yaml
single_scientist:
  persistence: medium
  sequences: 3
  effort_mode: fixed_passes
  context_policy: continue
```

Variant overrides take precedence over base settings; a CLI override takes precedence for
that invocation. Effective choices enter the configuration snapshot and saved study inputs.
There is no automatic selection of persistence levels or changes to lab organization.

An explicit `--sequence-context fresh_sequence` option starts a fresh model context at each
sequence boundary. This is optional; the default and supplied templates continue context.
Context resets are logged and do not delete earlier outputs, receipts or exposure history.
They do not make reused development cases statistically independent.

## Persistent work until the budget allowance

```bash
python3 engine.py run --variant scientist-persistent --sequences 3 --effort-mode budget
```

Budget mode is available for the persistent level. It continues passes until the current
sequence's request or time allowance is reached. Before each sequence, the controller divides
remaining requests and time over the remaining sequences. For example, a 12-request budget
and three sequences give request allowances of four each. Decisions, fallbacks and corrections
consume those allowances too. If an earlier sequence returns time or requests unused, later
sequences share the remainder.

All modes keep the user's global request, evaluation and wall-time limits. Sequence boundaries
never replenish them. Evaluators retain their existing shared development/confirmation limits;
request/time allocation is checked before provider dispatch. Long domain evaluations retain
the adapter's shared deadline. A request that fails with uncertain execution is not retried
automatically. Unexpected transport, protocol or evaluator failures stop the trial.

The budget mode records a partially finished last episode when its allowance is reached;
its prior requests and tool receipts remain in the journal. A controlled allowance boundary
is separate from an execution failure and from a verified research result. Fixed-pass mode
instead records an incomplete run if a shared limit prevents the planned passes from finishing.

The template's default cap is 32 requests and 900 seconds across the entire trial. Selecting
more sequences does not raise those caps. Choose a suitable budget explicitly. Budget-driven
mode requires at least one request per selected sequence.

## Preview the chosen setup

```bash
python3 engine.py visualize --variant scientist-medium --sequences 3
python3 engine.py visualize --variant scientist-persistent --sequences 3 --effort-mode budget
```

No model calls occur. The process monitor shows the persistence level, sequence count, effort
mode and context policy in the setup panel, plus current sequence/pass progress during work.
Fixed mode expands the passes into a serial graph. Budget mode shows one loop boundary per
sequence; its actual pass count follows observed activity. Saved trials retain their recorded
settings. Use the same CLI overrides for visualization and execution to follow a matching run.
The comparison export records persistence, effort mode, planned/completed sequence counts,
completed passes, context policy and configuration identity. Reusing a variant name with
different CLI overrides therefore keeps the actual settings visible; no automatic ranking is added.

From a checkout, inspect a structural plan directly:

```bash
teamknitt engine --project . plan --design lab_designs/F-single-scientist.md \
  --persistence medium --sequences 3
```

The `single_scientist` controls affect design F only. Adding scientist instances or enabling
delegation is rejected for that design. Other presets keep their existing work graphs.

## Scientific execution and confirmation

The supplied scientist template is text-only. Registered domain adapters remain necessary
for actual experiments; the three effort settings do not grant arbitrary code execution.
For a domain study, select F in that study's lab configuration and remove incompatible persona
overrides. Optional decision models keep their existing permission, credential and budget rules.

Development in every selected sequence ends before one controller-owned final confirmation,
when the domain and remaining budgets support it. Confirmation feedback never returns to the
acting scientist. Repeated sequences cannot adapt to an already-exposed final panel.
Statistical methods and conclusions still belong to the declared evaluation protocol.
