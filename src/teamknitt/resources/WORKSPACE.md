# Your teamknitt workspace

Configure and monitor a team for **your task, brainstorming prompt or goal**. Labtune is
its engine and aesthetic foundation; you do not need to turn every task into a research lab.

1. Edit `mission/task.md`: your brief and desired result. Add context in `mission/context.md`.
2. Choose `team.topology`, `team.members` and `communication` in `team.yaml`.
3. Inspect locally: `teamknitt view --workspace .` or `python team.py check`.
4. Demonstrate locally: `python team.py demo` (deterministic fixture, no model calls).
5. For a real run, choose your model/provider/limits in `study.yaml`, set the named private
   key, then explicitly authorize `python team.py run --live --approve-requests 24`.
   The number must equal your own engine request cap. It is not a currency cap.

Topologies: fully connected, hub-and-spoke, ring, hierarchical routing, or custom directed
links. Choose 1–16 members. Sharing: none, low, intermediate, high, or wisdom-only.
Larger teams do not cause automatic budget increases. A hierarchy routes communication;
it does not automatically grant decision authority. With no sharing, contributions remain
independent for your review.

Draft a change without modifying files:

```bash
teamknitt configure --workspace . --members 4 --topology ring --communication intermediate
```

Review the draft; to apply, add **`--apply --reset-cognition`**. This explicitly regenerates
starter cognitive bindings, privately backs up the prior configuration, and leaves your
brief text and engine/model/budget settings unchanged. Customize cognition directly in YAML
when you want role-local inputs, different work dependencies or handoffs instead.

Distributed team cognition organizes responsibilities, representations, expertise directories
and handoffs. Optional `observations` add the dynamical-systems lens: local/global activity,
perturbation response, coupling and cross-level records. Attractors, synchronization and
fractals are identified as **not estimated**, not fabricated from a short run. Set
`observations.enabled: false` to disable these derived tools. They are not an overall score.

The viewer follows matching execution metadata when available. It never calls models or
writes a draft automatically. `trials/ID/deliverable.md` contains private team contributions;
completion of execution is not proof your task/goal is achieved. You review that result.
Keep `.env`, trials, generated results, config backups and snapshots out of Git.

## Licensing notice — unchanged

Author: **Goran Mitevski**. Copyright holder/licensor: **Pioneertown B.V.** Read **LICENSE** and
**LICENSING.md**. The Labtune Academic Research License 2.0 limits free use to qualifying
public/nonprofit academic institutions in World Bank low-income or lower-middle-income
economies and authorized users for independent noncommercial research. The wider task/goal
scope is **not** permission for commercial use. Company labs, corporate proxies and commissioned
company work remain excluded. Company donations must be unrestricted, without control or
privileged research/IP rights. Other use requires written permission through Goran Mitevski,
**goran@pioneertown.ai**, on behalf of Pioneertown B.V. Preserve both license texts and credits.
