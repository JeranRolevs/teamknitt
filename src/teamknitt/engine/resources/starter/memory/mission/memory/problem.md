# Useful reference memory under a fixed budget

Develop a causal retention policy that improves a streaming distance detector at the same
persistent-state and compute limits as FIFO and reservoir memory. Retain infrequent normal
patterns, adapt to benign drift and returning regimes, and preserve sensitivity to faults.
The useful result is an executable policy with measured improvements or a clear failure
mechanism. Publishing and choosing a winning lab organization are not mission objectives.

## What the lab generates

The configured generation model authors policy source through experiment.run. Optional
decision.assess calls use the selected endpoint, then the same generation model resumes.
Administration stays outside the research-generation provider. Your PC evaluates policies in a separate OS-sandboxed
process. Submit real source rather than selecting an existing window preset.

The first version isolates retention. The trusted scorer, synthetic generator, calibration
rule and budget accounting are fixed. A policy selects observations to retain and may carry
32 auxiliary numbers. Learned prototypes, compression and changes to the scorer are later
extensions; do not claim them implemented by this API.

## Public interface

```python
def select(bank, ages, new, t, capacity, aux):
    # Return unique indices into bank + [new], and <=32 auxiliary numbers.
    return {"keep": [...], "aux": [...]}
```

The scientific tool contract specifies permitted Python operations. No imports or file/network
access. The namespace is fresh per call; only the declared memory and aux persist. Retain
between one and capacity available vectors. Source size is at most 16,384 UTF-8 bytes.
Current input has already been scored against OLD memory before this update executes.

## Evaluation data

Observations are non-overlapping 16-sample vectors. Four synthetic families contain infrequent
benign recurrence, gradual drift, returning regimes, and mixtures. Normal modes have examples
during warmup. Recurrence periods exceed the small FIFO capacity. Fault runs contain one
labelled spike, shape change or level change at an undisclosed onset.

These are defined synthetic mechanisms, not a claim that univariate observations can always
identify the real-world cause of a change. Transfer to ESA comes after successful controlled
tests and keeps Anomaly and Rare Event labels separate.

Only past observations, their indices, capacity and declared state enter the policy process.
Labels, random seeds, family IDs, future samples and split identity stay with the evaluator.
Development and confirmation seeds are disjoint and private. Every algorithm uses matched
instances. No seed manifest is included in model prompts.

## Primary measures

- Any alarm during a fixed-horizon benign run: k/n with CP95.
- Fault detected within its labelled interval: k/n with CP95 and delay in observation ticks.
- Any alarm on a benign recurrence within a null run: k/n with CP95.
- Results by family, calibration count, numeric-state bytes, worker peak RSS, worker CPU and
  total evaluator wall time. Source bytes and all failed candidates remain visible.

Calibrate candidate-specific thresholds using maxima of separate event-free runs. Never fit
thresholds on scored null/fault runs. Target is 10% probability of any alarm within the declared
finite horizon, not 10% of points and not a perpetual-operation guarantee. No quiet segments
are silently removed. Each denominator is independent generated runs, not correlated points.

The smoke profile uses capacity 24, 192 ticks, 48 warmup ticks, 24 calibration runs and 12 each
null/fault runs, at 10% only. Its intervals are wide: it tests execution, not research success.
The full profile uses 384 ticks, 64 warmup ticks, 200 calibration and 100 each null/fault runs,
with 10%, 3%, 1% targets. Full cases have 8, 16 or 40 benign modes (sometimes exceeding
capacity), less frequent recurrence and weaker faults. Do not pool the two profiles.

Within one lab run, confirmation selection is declared before search: minimize development
false-alarm excess above 10%, then maximize fault recall, then minimize calibration error.
These are exploratory point estimates, not a statistical acceptance test. One fixed candidate
is confirmed after agent work ends; confirmation results never return to those agents.

## Comparison of lab organizations

The user selects styles and communication. Keep the generation model, request options, decision mode,
problem instances and total budgets matched; record realized compute. Include a single-agent
agent baseline without child delegation. Repeat independent lab runs; first compare styles
with sharing held fixed, then vary sharing within a style. No automatic lab-redesign loop,
configuration freezing or winner selection is permitted.
