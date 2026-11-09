# Optional teammate-behavior experiments

This standalone teamknitt application provides original synthetic alone/baseline/challenged
probes, informed by *Measuring AI Agents as Teammates with Collaborative Intelligence*.
It is not the official benchmark, its implementation or a measure of general psychological traits.

The main overview places this behavioral perspective under **Standard**, alongside shared
models/member reports. **Complexity** groups distributed problem-solving, team dynamics and
interaction/coordination. Neither group starts these experiments automatically.

```bash
teamknitt probes init ../optional-probes
teamknitt probes check --workspace ../optional-probes
teamknitt probes demo --workspace ../optional-probes --policy fragile
teamknitt probes view ../optional-probes/runs/RUN_ID
# Attach a saved summary to a different task context, without running an evaluation:
teamknitt view --workspace TASK --group standard --probe-run PROBE_RUN
```

Explicit protocol/model/budget choices are in this separate workspace. Live execution still
requires explicit authorization. Eligibility uses alone performance; incomplete cells are
unknown, not zero-filled. Fixtures are illustrative software behavior, not model evidence.
Attached results remain separate-context evidence, not a score for the selected task team.

Based on Labtune; the engine is shipped under teamknitt.engine and no upstream package is
required. Keep credentials, natural-language records, runs and results private and outside Git.

## Licensing notice — unchanged

Author: **Goran Mitevski**. Copyright holder/licensor: **Pioneertown B.V.** Preserve LICENSE,
LICENSING.md and these credits. The **Labtune Academic Research License 2.0** remains unchanged:
free use is limited to qualifying public/nonprofit academic institutions in World Bank
low-income or lower-middle-income economies and authorized users for independent noncommercial
research. Company labs, corporate proxies and commissioned company work are excluded. Other
use requires written permission through Goran Mitevski, goran@pioneertown.ai, on behalf of
Pioneertown B.V. Broader task capability does not broaden eligibility or permit commercial use.
