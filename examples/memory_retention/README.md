# Synthetic memory-retention research task

This independent example asks how to retain infrequent normal patterns while adapting to drift
under bounded state and compute. A configured generation model writes policy source; a trusted
supervisor evaluates it in a separate sandbox. The user chooses the model, lab style, sharing,
optional decision endpoints and budgets. No model account or live call is part of setup.

```bash
python3 -m pip install -e '.[memory]'
teamknitt engine init ../memory-lab --template memory
cd ../memory-lab
python3 engine.py prepare
python3 engine.py qualify
```

Candidate execution requires native macOS sandbox qualification. Configure the generic
provider section of study.yaml and the private .env key before an explicit run, for example
python3 engine.py run --variant memory-single. The default uses LLM-only judgments; separate
chat or typed decision endpoints can be selected explicitly. No service or model is bundled.

The task ships public generators, baselines, evaluator scripts and protocols. Fresh private
calibration, development and confirmation seed panels are generated at initialization and
must remain local. Candidate code sees only causal observations and bounded retained state;
labels, future inputs and credentials stay with the trusted supervisor.

Read mission/memory/problem.md, EVALUATION.md and FLOW.md before running. The full profile
and 45-variant matrix are optional choices, not automatic batches. Fixed candidate source is
confirmed only after development, without feeding confirmation results back to actors.
Receipts record provenance, counts, uncertainty, memory, time and failures. Pipeline checks
are not evidence that a particular lab style or candidate is scientifically superior.
