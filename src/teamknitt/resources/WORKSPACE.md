# Your teamknitt workspace

teamknitt is a standalone engine for **your task, brainstorming prompt or goal**. Based on
Labtune; see PROVENANCE.md. It does not require another package or command.

1. Edit `mission/task.md` and optional `mission/context.md`.
2. Choose topology, member count, sharing and explicit bindings in `team.yaml`.
3. Inspect with `teamknitt view --workspace .` or `python team.py check`.
4. Run `python team.py demo` for a transparent software fixture, no model calls.
5. For real execution, explicitly choose provider/model/limits in `study.yaml`, set your
   declared private key, and authorize `python team.py run --live --approve-requests N`.
   N must equal your resolved request cap, not an automatically recommended budget.

Fourteen routing presets support 1–16 members. Use `teamknitt topologies`; examples include
rings/chains, wheel, grid, clustered pods, bipartite, broadcast/gather and custom links.
Sharing profiles are none, low, intermediate, high and wisdom-only. Larger teams do not
raise limits, and topology does not grant decision authority or erase previous exposure.

Preview with `teamknitt configure --workspace . --members 6 --topology grid`. Apply only after
review with `--apply --reset-bindings`: it privately backs up and regenerates starter
bindings while preserving brief text, models and budgets, and respects the run lock.

**Standard** groups collaborative intelligence and shared-model/member reports. **Complexity**
groups distributed problem-solving, team dynamics and interactions/coordination. Choose with
`view --group standard|complexity --section NAME`; switching changes no configuration and
starts no evaluation. `--probe-run PATH` optionally attaches a separate saved protocol,
not capabilities attributed to this team or an official CIB score. Fixtures are not model evidence.

Optional observations remain descriptive; attractors, synchrony and fractals are not estimated.
Set `observations.enabled: false` to disable derived tools. Source/generated text and the
private `trials/ID/deliverable.md` require your review; execution is not proof of task success.
Bayesian/probabilistic analysis is not available and unsupported legacy selections are rejected,
not converted. See `docs/TEAMKNITT.md` for controls, references and interpretation boundaries.

Keep credentials, trials, results, config backups, migration backups and snapshots out of Git.

## Licensing notice — unchanged

Author: **Goran Mitevski**. Copyright holder/licensor: **Pioneertown B.V.** Read **LICENSE** and
**LICENSING.md**. The Labtune Academic Research License 2.0 limits free use to qualifying
public/nonprofit academic institutions in World Bank low-income or lower-middle-income
economies and authorized users for independent noncommercial research. The wider task/goal
scope is **not** permission for commercial use. Company labs, corporate proxies and commissioned
company work remain excluded. Company donations must be unrestricted, without control or
privileged research/IP rights. Other use requires written permission through Goran Mitevski,
**goran@pioneertown.ai**, on behalf of Pioneertown B.V. Preserve both license texts and credits.
