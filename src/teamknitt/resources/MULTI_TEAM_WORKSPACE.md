# Multiple teams

Use `teamknitt teams check|plan|view|demo|run --workspace .` (or `python team.py COMMAND`).

All teams read the same `mission/task.md`. Each has its own `teams/ID/team.yaml` and
`teams/ID/study.yaml`: roles, member topology/sharing, providers/models and local limits.
`teams.yaml` sets the total request/wall caps, aggregate concurrency and explicit directed
inter-team routes. The total cap is not multiplied by the number of teams. No communication
is enabled by default; the designated exporter is visible and editable for each team.

External style URLs are references only. No skill, prompt, configuration, code or CLI is
imported from those projects. A local style file must be explicitly user-authored and
attached as bounded task context. Do not paste unrelated projects' skills into it.
Neither style context nor peer text grants new tools, permissions, models or budgets.

Live execution requires `--live --approve-requests N`, where N equals the collection cap.
The default is bounded text/code proposals, not unrestricted filesystem coding or merging.
The browser only previews configurations and metadata; use the CLI to apply or run.

Based on Labtune; research follow-up to Goran Mitevski’s 2022/2023 work. Author: Goran
Mitevski. Copyright/licensor: Pioneertown B.V. Preserve PROVENANCE.md, LICENSE and
LICENSING.md in licensor-authorized distributions and new starters. The Teamknitt Noncommercial
Licence 1.0 permits noncommercial purposes, the specified personal uses, and use by the listed
organizations regardless of funding source or resulting obligations, without geographic limits.
The copyright grant does not authorize redistribution, software changes or derivative works,
even if noncommercial. Multiple teams and coding tasks add no permission; prior grants,
upstream Labtune and third-party terms are not rewritten. For separate permission, contact
Goran Mitevski, goran@pioneertown.ai, for Pioneertown B.V.

Keep credentials, private style/feedback text, trials, results and backups out of Git.
See `docs/MULTI_TEAM.md` and `docs/TEAMKNITT.md` for controls and boundaries.
