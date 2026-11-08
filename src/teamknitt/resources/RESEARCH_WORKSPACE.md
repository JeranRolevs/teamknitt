# Your Teamknitt distributed-cognition workspace

**Labtune is the baseline.** The handbook *Foundations and Theoretical Perspectives of
Distributed Team Cognition* supplies the configuration perspective. *Teams As Dynamical
Systems* informs interaction and change through time. This workspace is not a teammate benchmark.

## Inspect and configure before execution

```bash
python team.py check
python team.py plan
python team.py prepare
teamknitt view --workspace .
```

- **`study.yaml`, `configs/lab.yaml`, `lab_designs/`**: the original Labtune organization,
  model, communication, delegation, statistics and budgets. The selected co-leader design
  and high-detail sharing are editable example choices, not performance recommendations.
- **`team.yaml`**: binds an existing Labtune variant/persona instances to work responsibilities,
  complementary source inputs, shared external representations, an expertise directory,
  versioned handoffs, explicit temporal expectations and action opportunities.
- **`mission/problem.md` and `mission/cognition/*.md`**: replace starter material with your
  actual mission and researcher-supplied context. The notes are illustrative inputs, not findings.

Switch a design/count in Labtune and explicitly rebind the cognition roles. The overlay
never grants broader sharing, selects another model or increases budgets to make a plan fit.
For an explicit unitary / independent-contribution alternative, copy
`configurations/independent-contributions.team.yaml` to `team.yaml`. It selects the
already-declared `independent` Labtune variant with no peer research sharing and private
notes. No automatic aggregation or configuration ranking is performed.

## Offline process demonstrations

```bash
python team.py demo --policy connected
python team.py demo --policy fragmented
teamknitt view trials/RUN_ID
```

Both use the selected Labtune graph with deterministic local responses and **zero provider
calls**. They demonstrate representation flow, handoffs and explicit-plan mismatch—not agent
quality, latent mental models or scientific correctness. A configuration can be viewed without
running either fixture. Use `--output NEW.teamknitt.html` for a new private offline snapshot.

## Live research, only by explicit authorization

Choose provider/model and budgets in `study.yaml`. Set the named private environment key or
local `.env` (never in Git/YAML). Replace `AWAITING_USER_PROBLEM`, review the plan and then:

```bash
python team.py run --live --approve-requests 16
```

Replace `16` with your own resolved Labtune `budget.max_llm_calls`. Requests include inherited
decision/fallback/tool behavior; no extra judge or model service is added by Teamknitt. This is
not a currency cap. Domain research requires the original Labtune adapter's qualification and
evidence rules. A completed text workflow is not a verified research finding.

The original `python lab.py prepare|doctor|qualify|run|compare|visualize` commands remain.
Optional teammate-behavior probes use `teamknitt probes` and separate workspaces/configs;
they do not determine this workspace's configuration or require an alone/baseline/test protocol.

Keep `.env`, `trials/`, `runs/`, private panels, results and exported HTML out of Git.
The viewer omits note text and private inputs, but even metadata may be sensitive.
Read `docs/TEAMKNITT.md` for configuration boundaries and source references.

## Licensing notice

Author: **Goran Mitevski**. Copyright holder and licensor: **Pioneertown B.V.**
The **Labtune Academic Research License 2.0** is unchanged. Free use is limited to qualifying
public or nonprofit academic institutions in World Bank low-income or lower-middle-income
economies and their authorized users for independent noncommercial research. Company labs,
corporate research proxies and commissioned company work are excluded. Company donations
must be unrestricted, without control or privileged research/IP rights. Other use requires
separate written permission through Goran Mitevski, **goran@pioneertown.ai**, on behalf of
Pioneertown B.V. Preserve LICENSE, LICENSING.md and these credits. Research outputs are not
relicensed merely through use. The license texts control.
