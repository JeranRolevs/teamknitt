# Optional teammate-behavior probes — secondary to Teamknitt's cognition layer

This separate application retains the initial synthetic alone/baseline/challenged protocol,
informed by *Measuring AI Agents as Teammates with Collaborative Intelligence*. It is **not**
the Teamknitt configuration backbone or the official Collaborative Intelligence Benchmark.
The main product configures distributed cognition on Labtune using the McNeese–Salas–Endsley
handbook, extended by the dynamical-systems perspective. You do not need these probes to use it.

Create a **separate** probe workspace:

```bash
teamknitt probes init ../optional-probes
teamknitt probes check --workspace ../optional-probes
teamknitt probes demo --workspace ../optional-probes --policy coordinated
teamknitt probes demo --workspace ../optional-probes --policy fragile
teamknitt probes view ../optional-probes/runs/RUN_ID
```

Only this optional schema-version-1 workspace uses a focal subject, controlled scripted
teammate, eight public arithmetic/ledger task families and repeated challenged conditions.
Structured action labels are narrow software probes, not validated empathy or human-team
constructs. Fixture scores are not model evidence. Do not mix this `team.yaml` with the main
schema-version-2 distributed-cognition workspace. The old schema is not automatically migrated.

Preparation, fixtures and visualization make no provider calls. For any explicitly selected
live probe, configure its own providers and then use
`teamknitt probes run --workspace ../optional-probes --live --approve-requests 504`.
The approval must match that workspace's own request cap. It is not a currency estimate.
All failures, eligibility denominators and missing cells remain explicit; no official benchmark
result or improvement in research quality is claimed. Private records stay in ignored `runs/`.

Author: **Goran Mitevski**. Copyright holder/licensor: **Pioneertown B.V.** Preserve LICENSE,
LICENSING.md and these credits. The Labtune Academic Research License 2.0 is unchanged: free
use is limited to qualifying public/nonprofit academic institutions in World Bank low-income
or lower-middle-income economies and authorized users for independent noncommercial research.
Company labs, corporate proxies and commissioned company work are excluded. Company donations
must be unrestricted, without control or privileged research/IP rights. Other use requires
written permission through **goran@pioneertown.ai**, Goran Mitevski, on behalf of Pioneertown B.V.
