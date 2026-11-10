# Teamknitt

Configure teams of 1–16 LLM agents from a conversation with Claude: set the task, choose who
talks to whom, decide how much they share and what budget they get, then follow the work and
intervene. The plugin contains one skill, `teamknitt`, and a copy of the teamknitt command-line
tool that the skill installs and operates for you.

teamknitt is built around explicit human choices. Claude drafts and previews; you decide. Nothing
is applied, and no model is called, without your say-so. There is no automatic team redesign,
model selection, budget increase or team-quality score.

## Use it

Ask Claude in plain words, for example:

- "Set up a teamknitt team of four agents in a ring to brainstorm welcoming workshop formats, and
  show me the plan."
- "Change my team to six members in clusters and show me what would change before applying it."
- "Create three separate teams of two for the same task with a shared cap of 24 requests, and let
  the first team send summaries to the second."

Claude will then:

1. Install the bundled teamknitt tool in the session (Python 3.11 or newer).
2. Agree the purpose, team size, topology and sharing level with you. There are 13 routing
   presets (ring, hub and spoke, chain, grid, clusters and more) plus custom links.
3. Create a workspace, check it and report the plan, including the cap on model requests.
4. Save an offline HTML snapshot of the team for you to open, or start the local viewer on your
   own machine.
5. Preview any change first and apply it only after you agree.
6. Run an offline demonstration, or a live run once you have set a provider and approved the cap.
7. Help you read the results, pause, stop or give feedback to a running team.

## Install

In Claude Code:

```
/plugin install teamknitt --marketplace JeranRolevs/teamknitt
```

On claude.ai, add the marketplace `https://github.com/JeranRolevs/teamknitt` under
Customize > Plugins, then install Teamknitt from it.

## What it runs, fetches and sends

- **Runs:** the bundled `teamknitt` Python package, copied from the skill's `runtime` folder in
  this plugin and installed into a private virtual environment in your home folder. All source
  is included here in readable form.
- **Fetches:** when installing, `pip` downloads two dependencies from PyPI, PyYAML and
  jsonschema. The plugin fetches nothing else and loads no instructions from the network.
- **Sends:** nothing by default. Setup, checking, planning, viewing, previews and demonstrations
  are fully offline. Only a live run (`teamknitt run --live`), which you must explicitly approve
  with the request cap, sends your brief, context and the agents' messages to the model service
  that you chose and configured in the workspace, using your own key.
- **Credential:** for a live run the tool reads one API key, from the environment variable named
  in the workspace's `study.yaml` (by default `TEAMKNITT_API_KEY`) or from the workspace's `.env`
  file. The key is sent only as the `Authorization` header to the model service address you set
  as `base_url` in that workspace. Redirects are not followed with the key, and the key's value is
  redacted from run records.
- **Stores:** workspaces and run records are ordinary files in the folder you choose. Your key
  stays in the workspace's `.env` file, which you fill in yourself. The plugin collects no data,
  has no telemetry and contacts no server of its author.

A live run needs a chat-completions-compatible model service and normally runs on your own
machine (for example in Claude Code). In a chat sandbox Claude prepares and checks the workspace
and hands it to you with the command to run.

## Support

- Issues and questions: <https://github.com/JeranRolevs/teamknitt/issues>
- Author: Goran Mitevski, <rolevski.mk@icloud.com> ·
  [LinkedIn](https://www.linkedin.com/in/goran-ptbv)

## Licence

This plugin is offered under the **Teamknitt Skill Licence 1.0** ([LICENSE](LICENSE),
[guide](LICENSING.md)). Anyone may use the unmodified skill in Claude for any purpose, including
commercial work and research. At this stage it covers Claude only and does not allow changing
the skill. Use of the teamknitt code apart from the skill stays under the Teamknitt Noncommercial
and Research Licence 2.0, a copy of which is included with the bundled runtime.

Copyright holder and licensor: Pioneertown B.V. Author: Goran Mitevski. Based on Labtune. This
is an independent work; it is not made, endorsed or supported by Anthropic.
