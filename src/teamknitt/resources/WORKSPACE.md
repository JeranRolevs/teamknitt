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

**Non-system** groups collaborative intelligence and shared-model/member reports. **System**
groups distributed problem-solving, differentiated transactive memory, interactive team
cognition/coordination and dynamics. Choose with `view --group non_system|system --section NAME`;
historical group aliases still work. Switching changes no configuration or evaluation.
`--probe-run PATH` attaches separate saved evidence, not capabilities attributed to this team.
Human-team theory informs design; emergence and psychological states are not inferred.
See `docs/TEAM_RESEARCH.md` and offline `teamknitt theory`.

Use the **Intervene** desk to prepare explicit commands and inspect receipts. From this workspace:

```bash
# Preview; only add --apply after review to queue each selected request.
teamknitt intervene trials/RUN_ID --action feedback --message-file mission/feedback.md --actors member.1
teamknitt intervene trials/RUN_ID --action pause
teamknitt intervene trials/RUN_ID --action resume
teamknitt intervene trials/RUN_ID --action stop
# Future-run disturbance, also draft by default:
teamknitt schedule --workspace . --id reviewed-gap --kind actor_unavailable --target member.1 --at-wave 4 --duration 1
```

Current-wave work may finish. Pause/resume keeps the same run, lock, counters and wall deadline;
stop is terminal and preserves partial contributions. Feedback grants no new tool/source rights.
A queue receipt or context assembly is not proof of understanding or an improvement effect.
The browser does not apply these commands or start execution. See `docs/TEAMKNITT.md`.

Optional observations remain descriptive; attractors, synchrony and fractals are not estimated.
Set `observations.enabled: false` to disable derived tools. Source/generated text and the
private `trials/ID/deliverable.md` require your review; execution is not proof of task success.
Bayesian/probabilistic analysis is not available and unsupported legacy selections are rejected,
not converted. See `docs/TEAMKNITT.md` for controls, references and interpretation boundaries.

Keep credentials, trials, results, config backups, migration backups and snapshots out of Git.

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
