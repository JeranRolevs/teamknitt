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
Read **LICENSE** and **LICENSING.md**. The **Teamknitt Noncommercial and Research Licence 2.0**
provides free general noncommercial, non-research use. The research exception overrides that
grant: noncommercial research outside qualifying low-income/lower-middle-income academic
institutions requires separate written permission. Free research retains Labtune's qualifying
institution/affiliation, current World Bank income, independent-governance, funding and
anti-circumvention conditions. Company research/proxies and privileged sponsor rights do not
qualify; company research donations must be genuinely unrestricted. Commercial use also
requires separate permission from Pioneertown B.V. through Goran Mitevski, **goran@pioneertown.ai**.

Use, copying, study, modification and sharing are allowed for Permitted Uses without a software
licence fee. Retain the legal, author/copyright and third-party notices, identify changes and
distribute software changes under the same terms. Sharing does not transfer research eligibility.
Fair use, reserved rights, automatic termination/written reinstatement and warranty/liability
limits apply. Earlier grants (including version 1.0), existing copies/workspaces, upstream
Labtune and third-party terms are not rewritten. Mode labels and instructions do not add rights.
