# Memory-policy evaluation contract

The task version is memory_policy.v1: observation retention plus bounded numeric auxiliary state.
The detector computes minimum root-mean-square distance to retained past vectors. It scores
before update, preventing a current vector from becoming its own reference.

Calibration maxima cover the complete scored horizon of independent benign runs. Rank is
ceil((n+1)*(1-alpha)) in ascending order. An unavailable finite rank is reported as insufficient
calibration. Under exchangeability this gives a marginal exceedance bound; it is not a
conditional or arbitrary-drift guarantee. Exact CP95 summaries accompany independent-run
counts. Bayesian analysis is not supported by teamknitt; no prior/posterior option is exposed.

The synthetic family includes both nuisance changes and faults with known mechanisms. Benign
recurrence locations and fault locations are defined by generation, not inferred from ESA
Rare Event labels. Every fault has a paired counterfactual construction: the same seed without
injection preserves all observations outside the labelled interval. The benchmark does not
claim operational safety or universal cause identification from one channel.

Capacity 24 and dimension 16 permit at most 3,520 logical numeric-state bytes:
24*(16+1)*8 + 32*8. This counts packed numeric vectors, ages and aux, not Python interpreter
overhead. All policies share the same representation and source limit. Peak process RSS is
reported separately and checked against 128 MiB by a watchdog and completed-run accounting.
Per-response timeout is two seconds and per-worker CPU limit 120 seconds. Unsupported macOS
address-space/data rlimits are not claimed as enforced memory ceilings.

The trusted supervisor never execs submitted code. Its subprocess holds labels and private
seeds and sends only observations to a separate interpreter. That interpreter uses Python
isolated mode without site initialization, an AST-constrained API and an OS allowlist for
runtime files and the policy/contract/worker source. No file writes, network or process fork.
The supervisor itself is trusted local infrastructure; candidate code runs only inside the
sandbox. AST restrictions enforce the contract and are not presented as the OS security boundary.

Comparators are FIFO and reservoir under the primary budget. Growing memory is an explicitly
out-of-budget diagnostic. All use identical generated panels and their own separate calibration.
A good candidate must show a useful tradeoff against comparators; changing wording or copying
a baseline does not establish novelty. Diagnostic failure and duplicate compute remain results.

The first smoke does not execute confirmation cases. Proper organization comparisons use the
full profile, repeated lab runs, matched task instances and one runtime version. Differences
in communication, decision-endpoint availability, thinking settings or resource accounting are explicit
experimental variables, not unrecorded changes. Choose an applicable supported comparison
analysis before examining held-out style differences.

Files:
- evaluation-smoke.yaml and evaluation-full.yaml: public protocol versions.
- private_splits.json: mode 0600, Git-ignored, disjoint seeds, never model-visible.
- setup/memory_qualification/current.json: sandbox/instrument checks and development comparators.
- trials/<id>/experiments/: candidate.py, source hash, authorship, full receipts and sandbox logs.

The smoke generator uses four normal modes and strong faults. Full research cases randomize
8/16/40 normal modes, including cases beyond the 24-vector capacity, and weaker faults.
The full generator therefore tests a coverage/adaptation tradeoff rather than only the easy
case where one prototype per mode fits comfortably. These are separate named study profiles.

Confirmation calibration semantics: Development and confirmation use disjoint panels, each
with separate clean calibration runs and separate scored null/fault runs. The selected policy
source is fixed before confirmation. Its threshold is refitted on the unused confirmation
calibration panel, never on scored confirmation runs. Thus confirmation tests the fixed
policy plus the declared calibration procedure; it does not test transporting the numerical
development threshold without recalibration. The authoring smoke did not use confirmation.
