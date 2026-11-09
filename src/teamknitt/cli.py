"""User-directed team configuration and monitoring, powered by the teamknitt engine."""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys

from teamknitt.engine.config import ConfigurationError
from teamknitt.engine.providers.http import ProviderError
from teamknitt.engine.research import ResearchError
from teamknitt.engine.study import StudyError, save
from . import __version__
from .builder import PURPOSES, draft_configuration, apply_configuration
from .config import PERSPECTIVES, compile_plan, load
from .observatory import serve, snapshot
from .reporting import build_report, plan_report
from .runtime import run
from .scaffold import init
from .topology import TOPOLOGIES, TOPOLOGY_CATALOG
from .views import VIEWS, GROUPS, resolve_view, catalogue, load_probe_summary, with_views, COMPLEXITY_TRADITION, COMPLEXITY_SOURCES, SOURCES

PROFILES = ("none", "low", "intermediate", "high", "wisdom_only")


def choices(command, *, optional=True):
    command.add_argument("--topology", choices=tuple(TOPOLOGIES), default=None if optional else "fully_connected")
    command.add_argument("--members", type=int, default=None if optional else 3)
    command.add_argument("--communication", choices=PROFILES, default=None if optional else "high")
    command.add_argument("--purpose", choices=tuple(PURPOSES), default=None if optional else "brainstorm")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "engine":
        from .engine.cli import main as engine_main
        return engine_main(argv[1:])
    if argv and argv[0] == "probes":
        from .probes.cli import main as probe_main
        return probe_main(argv[1:])
    parser = argparse.ArgumentParser(prog="teamknitt", description="Configure and monitor teams for user tasks, brainstorming and goals. teamknitt is the engine.")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    start = commands.add_parser("init", help="Create a user-directed team workspace; no provider calls")
    start.add_argument("destination", type=Path)
    start.add_argument("--template", choices=("task", "research"), default="task")
    start.add_argument("--goal", help="User-supplied brief to write to the task file; otherwise edit it locally")
    choices(start, optional=False)
    commands.add_parser("engine", help="Advanced standalone execution, provider, domain and workspace commands")
    commands.add_parser("topologies", help="List user-selectable team communication topologies")
    commands.add_parser("perspectives", help="Inspect the distributed-problem-solving configuration framework")
    commands.add_parser("observations", help="Describe optional complexity/dynamics observations and their limits")
    commands.add_parser("views", help="Inspect Standard and Complexity approach groups and their focused views")
    commands.add_parser("lenses", help="Compatibility alias for views")
    commands.add_parser("probes", help="Optional synthetic teammate evaluation; never launched by an overview")
    migration = commands.add_parser("migrate", help="Preview local legacy-name migration; apply explicitly with a private backup")
    migration.add_argument("--workspace", type=Path, default=Path.cwd())
    migration.add_argument("--apply", action="store_true")
    configure = commands.add_parser("configure", help="Draft a topology/count/purpose change; apply only with explicit flags")
    configure.add_argument("--workspace", type=Path, default=Path.cwd())
    choices(configure)
    configure.add_argument("--max-read-words", type=int)
    configure.add_argument("--observations", choices=("on", "off"))
    configure.add_argument("--apply", action="store_true")
    configure.add_argument("--reset-bindings", dest="reset_cognition", action="store_true", help="Acknowledge regenerated role/representation/work bindings; the previous config is backed up")
    configure.add_argument("--reset-cognition", dest="reset_cognition", action="store_true", help=argparse.SUPPRESS)
    for name in ("check", "plan", "prepare", "demo", "run"):
        command = commands.add_parser(name)
        command.add_argument("--workspace", type=Path, default=Path.cwd())
        if name == "demo":
            command.add_argument("--policy", choices=("connected", "fragmented"), default="connected")
        if name == "run":
            command.add_argument("--live", action="store_true", help="Authorize metered calls with your selected engine settings")
            command.add_argument("--approve-requests", type=int, help="Must equal the engine's resolved budget.max_llm_calls")
    summary = commands.add_parser("report", help="Rebuild task-team process metadata and selected observations locally")
    summary.add_argument("run", type=Path)
    summary.add_argument("--probe-run", type=Path, help="Explicitly attach a separate saved probe record; never evaluate or attribute it to this team")
    view = commands.add_parser("view", help="Configure locally, inspect a workspace, or monitor matching execution; no provider calls")
    view.add_argument("run", type=Path, nargs="?")
    view.add_argument("--workspace", type=Path, default=Path.cwd())
    view.add_argument("--output", type=Path)
    view.add_argument("--group", choices=tuple(GROUPS), help="Standard or Complexity; presentation only")
    view.add_argument("--section", choices=tuple(VIEWS), help="Focused view within its approach group")
    view.add_argument("--lens", help=argparse.SUPPRESS)
    view.add_argument("--probe-run", type=Path, help="Attach separate saved protocol evidence, without prompts or messages")
    view.add_argument("--port", type=int, default=8766)
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            result = init(args.destination, template=args.template, topology=args.topology, count=args.members,
                          communication=args.communication, purpose=args.purpose, goal=args.goal)
        elif args.command == "topologies":
            result = {"topologies": TOPOLOGIES, "catalog": TOPOLOGY_CATALOG, "member_range": [1, 16], "automatic_selection": False, "api_calls": 0}
        elif args.command == "observations":
            from .observations import DIMENSIONS
            result = {"source": COMPLEXITY_TRADITION, "representative_sources": [SOURCES[k] for k in COMPLEXITY_SOURCES],
                      "dimensions": DIMENSIONS, "aggregate_score": None, "api_calls": 0}
        elif args.command == "perspectives":
            result = {"backbone": "Distributed problem-solving and related team-cognition traditions", "perspectives": PERSPECTIVES, "representative_sources": SOURCES, "api_calls": 0}
        elif args.command in {"views", "lenses"}:
            result = catalogue()
        elif args.command == "migrate":
            from .migration import migrate
            result = migrate(args.workspace, apply=args.apply)
        elif args.command == "configure":
            c = draft_configuration(load(args.workspace), topology=args.topology, count=args.members,
                communication=args.communication, purpose=args.purpose, max_read_words=args.max_read_words)
            if args.observations is not None:
                c["observations"]["enabled"] = args.observations == "on"
            compiled = compile_plan(args.workspace, c)
            result = apply_configuration(args.workspace, c, reset_cognition=args.reset_cognition) if args.apply else {
                "status": "configuration_draft_only", "configuration": c,
                "configuration_sha256": compiled["configuration_sha256"], "api_calls": 0,
                "warning": "No files changed. Applying regenerates starter cognitive bindings, not models/budgets or task text. Review and add --apply --reset-bindings."}
        elif args.command == "report":
            result = with_views(build_report(args.run), load_probe_summary(args.probe_run)) if args.probe_run else build_report(args.run)
        elif args.command == "view":
            report = build_report(args.run) if args.run else plan_report(compile_plan(args.workspace))
            probe_summary = load_probe_summary(args.probe_run) if args.probe_run else None
            group, section, notice = resolve_view(args.group, args.section, args.lens)
            report = {**with_views(report, probe_summary), "viewer": {"initial_group": group, "initial_section": section, "view_notice": notice}}
            result = snapshot(report, args.output) if args.output else serve(report, args.port,
                workspace=None if args.run else args.workspace, run_directory=args.run,
                initial_group=group, initial_section=section, view_notice=notice, probe_summary=probe_summary)
        elif args.command == "run":
            if not args.live:
                raise ConfigurationError("run requires --live and --approve-requests; use demo for an offline fixture.")
            result = asyncio.run(run(args.workspace, live=True, approve_requests=args.approve_requests))
        elif args.command == "demo":
            result = asyncio.run(run(args.workspace, policy=args.policy))
        else:
            plan = compile_plan(args.workspace)
            if args.command == "plan":
                result = plan
            elif args.command == "prepare":
                save(args.workspace / "plans/teamknitt.json", plan)
                result = {"status": "prepared", "plan": str((args.workspace / "plans/teamknitt.json").absolute()), "api_calls": 0, "task_started": False}
            else:
                result = {"status": "team_configuration_valid", "topology": plan["topology"],
                          "members": len(plan["topology"]["members"]), "configuration_sha256": plan["configuration_sha256"],
                          "provider_request_cap": plan["provider_request_cap"], "api_calls": 0, "task_started": False}
        print(json.dumps(result, indent=2, allow_nan=False))
        return 2 if result.get("status") in {"failed_or_incomplete", "cancelled"} else 0
    except (ConfigurationError, StudyError, ResearchError, ProviderError, OSError, ValueError) as error:
        print(f"teamknitt error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
