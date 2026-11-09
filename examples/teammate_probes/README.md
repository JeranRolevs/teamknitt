# Optional teammate-behavior experiments

This standalone teamknitt application provides original synthetic alone/baseline/challenged
probes, informed by *Measuring AI Agents as Teammates with Collaborative Intelligence*.
It is not the official benchmark, its implementation or a measure of general psychological traits.

The main overview places this behavioral perspective under **Non-system**, alongside shared
models/member reports. **System** groups distributed problem-solving, differentiated transactive
memory, interactive team cognition/coordination and dynamics. Neither group starts these experiments automatically.

```bash
teamknitt probes init ../optional-probes
teamknitt probes check --workspace ../optional-probes
teamknitt probes demo --workspace ../optional-probes --policy fragile
teamknitt probes view ../optional-probes/runs/RUN_ID
# Attach a saved summary to a different task context, without running an evaluation:
teamknitt view --workspace TASK --group non_system --probe-run PROBE_RUN
```

Explicit protocol/model/budget choices are in this separate workspace. Live execution still
requires explicit authorization. Eligibility uses alone performance; incomplete cells are
unknown, not zero-filled. Fixtures are illustrative software behavior, not model evidence.
Attached results remain separate-context evidence, not a score for the selected task team.

Based on Labtune; the engine is shipped under teamknitt.engine and no upstream package is
required. Keep credentials, natural-language records, runs and results private and outside Git.

## Research follow-up

teamknitt follows up Goran Mitevski’s **2022/2023 thesis research** on distributed teams and
their creative processes. The tool continues this work through team configuration,
work monitoring and human-directed intervention. See `docs/TEAM_RESEARCH.md`.

## Licensing notice

Author: **Goran Mitevski**. Copyright holder/licensor: **Pioneertown B.V.** Based on Labtune.
Read **LICENSE** and **LICENSING.md**. The **Teamknitt Noncommercial Licence 1.0** permits
noncommercial purposes, the specified personal uses without anticipated commercial application,
and use by the listed charitable, educational, public-research, public-safety/health,
environmental-protection and government organizations regardless of funding source or resulting
obligations. There is no geographic or academic-only eligibility test.

The copyright licence does **not** grant redistribution, software changes or derivative works,
even for noncommercial purposes. No sublicensing or transfer is granted; fair-use rights remain.
The patent grant/defense, conditional first-written-notice 32-day cure and as-is/no-liability
terms are in LICENSE. Workspace/development instructions do not add permission. Preserve both
legal documents and credits in licensor-authorized distributions and new starters; earlier
grants and third-party terms are not rewritten. For separate permission, contact Goran Mitevski,
**goran@pioneertown.ai**, for Pioneertown B.V.
