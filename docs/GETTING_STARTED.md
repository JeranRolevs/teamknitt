# Install and create a lab

Python 3.11+ is required. From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
teamknitt engine init ../my-lab
cd ../my-lab
python3 engine.py prepare
```

Windows users can activate .venv with .venv\Scripts\activate. Planning and text workflows
are portable. Candidate execution has a separate native macOS qualification requirement.
Initialization refuses to overwrite existing files and makes no model calls.

## Configure a service before running

Edit study.yaml to choose a compatible endpoint, model and budget. The .invalid URL and
YOUR_MODEL_ID placeholders intentionally prevent accidental live calls. Copy .env.example
to .env and set the configured private key, or explicitly choose unauthenticated access.
See [provider configuration](PROVIDERS.md) for the protocol and supported options.

Replace AWAITING_USER_PROBLEM in mission/problem.md with the research task and constraints.
Choose variants, sharing, delegation and statistics in study.yaml, then explicitly run:

```bash
python3 engine.py doctor
python3 engine.py run --variant single
python3 engine.py compare
```

The text starter variants are single, silos-high-wisdom and co-leaders-high-wisdom. Their
outputs are unevaluated proposals. doctor is local; doctor --live is a separate metered
connectivity check. [Decision endpoints](DECISION_PROVIDERS.md) are optional and user-configured.

## Single-scientist workspace

```bash
teamknitt engine init ../scientist-lab --template scientist
```

Choose scientist-low, scientist-medium or scientist-persistent. The user selects the number
of sequential runs with one context by default. Persistent effort supports fixed passes or
budget-driven work. [Single-scientist controls](SINGLE_SCIENTIST.md).

## Measured memory example

From the checkout, install python3 -m pip install -e '.[memory]', then:

```bash
teamknitt engine init ../memory-lab --template memory
cd ../memory-lab
python3 engine.py prepare
# Configure the chosen provider and budgets in study.yaml before qualification.
python3 engine.py qualify
```

The synthetic task includes a generator, public baselines, calibration/development/confirmation
protocols and OS-sandboxed policy source. It needs the memory extra and native macOS sandbox
qualification. There is no unsandboxed candidate fallback on unsupported platforms.
Initialization creates fresh private seed panels; no data, previous results or credentials ship.

With your chosen service configured and qualification current, set the private key and explicitly
select a variant such as memory-single.
The full profile and 45-variant matrix remain user choices and do not launch automatically.
Some matrix variants select separate decision protocols: configure those entries explicitly.
Use matched private panels and budgets for comparisons; unrelated seeds are not paired evidence.

## Records and observation

prepare writes plans/. A run writes trials/<id>/ with its inputs, configuration, events, actor
outputs, permitted sharing and evaluator receipts. compare writes comparisons/ without
inventing scores or choosing a winner. These folders and credentials stay outside Git.

python3 engine.py visualize --variant single opens a local process viewer using two read-only
agents. It makes no model calls. [Visualization and snapshots](VISUALIZATION.md).
