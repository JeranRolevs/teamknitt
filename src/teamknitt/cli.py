"""User-directed team configuration and monitoring, powered by the Labtune engine."""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys

from labtune.config import ConfigurationError
from labtune.providers.http import ProviderError
from labtune.research import ResearchError
from labtune.study import StudyError, save
from . import __version__
from .builder import PURPOSES, draft_configuration, apply_configuration
from .config import PERSPECTIVES, compile_plan, load
from .observatory import serve, snapshot
from .reporting import build_report, plan_report
from .runtime import run
from .scaffold import init
from .topology import TOPOLOGIES

PROFILES = ("none", "low", "intermediate", "high", "wisdom_only")


def choices(command, *, optional=True):
    command.add_argument("--topology", choices=tuple(TOPOLOGIES), default=None if optional else "fully_connected")
    command.add_argument("--members", type=int, default=None if optional else 3)
    command.add_argument("--communication", choices=PROFILES, default=None if optional else "high")
    command.add_argument("--purpose", choices=tuple(PURPOSES), default=None if optional else "brainstorm")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "probes":
        from .probes.cli import main as probe_main
        return probe_main(argv[1:])
    parser = argparse.ArgumentParser(prog="teamknitt", description="Configure and monitor teams for user tasks, brainstorming and goals. Labtune is the engine.")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    start = commands.add_parser("init", help="Create a user-directed team workspace; no provider calls")
    start.add_argument("destination", type=Path)
    start.add_argument("--template", choices=("task", "research"), default="task")
    start.add_argument("--goal", help="User-supplied brief to write to the task file; otherwise edit it locally")
    choices(start, optional=False)
    commands.add_parser("topologies", help="List user-selectable team communication topologies")
    commands.add_parser("perspectives", help="Inspect the distributed-cognition configuration framework")
    commands.add_parser("observations", help="Describe optional dynamical-systems observations and their limits")
    commands.add_parser("probes", help="Separate optional legacy teammate evaluation; not the teamknitt product workflow")
    configure = commands.add_parser("configure", help="Draft a topology/count/purpose change; apply only with explicit flags")
    configure.add_argument("--workspace", type=Path, default=Path.cwd())
    choices(configure)
    configure.add_argument("--max-read-words", type=int)
    configure.add_argument("--observations", choices=("on", "off"))
    configure.add_argument("--apply", action="store_true")
    configure.add_argument("--reset-cognition", action="store_true", help="Acknowledge regeneration of the starter role/representation/work bindings; the prior config is backed up")
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
    view = commands.add_parser("view", help="Configure locally, inspect a workspace, or monitor matching execution; no provider calls")
    view.add_argument("run", type=Path, nargs="?")
    view.add_argument("--workspace", type=Path, default=Path.cwd())
    view.add_argument("--output", type=Path)
    view.add_argument("--port", type=int, default=8766)
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            result = init(args.destination, template=args.template, topology=args.topology, count=args.members,
                          communication=args.communication, purpose=args.purpose, goal=args.goal)
        elif args.command == "topologies":
            result = {"topologies": TOPOLOGIES, "member_range": [1, 16], "automatic_selection": False, "api_calls": 0}
        elif args.command == "observations":
            from .observations import DIMENSIONS
            result = {"source": "Understanding and Modeling Teams As Dynamical Systems (Gorman et al., 2017)",
                      "dimensions": DIMENSIONS, "aggregate_score": None, "api_calls": 0}
        elif args.command == "perspectives":
            result = {"backbone": "Foundations and Theoretical Perspectives of Distributed Team Cognition", "perspectives": PERSPECTIVES, "api_calls": 0}
        elif args.command == "configure":
            c = draft_configuration(load(args.workspace), topology=args.topology, count=args.members,
                communication=args.communication, purpose=args.purpose, max_read_words=args.max_read_words)
            if args.observations is not None:
                c["observations"]["enabled"] = args.observations == "on"
            compiled = compile_plan(args.workspace, c)
            result = apply_configuration(args.workspace, c, reset_cognition=args.reset_cognition) if args.apply else {
                "status": "configuration_draft_only", "configuration": c,
                "configuration_sha256": compiled["configuration_sha256"], "api_calls": 0,
                "warning": "No files changed. Applying regenerates starter cognitive bindings, not models/budgets or task text. Review and add --apply --reset-cognition."}
        elif args.command == "report":
            result = build_report(args.run)
        elif args.command == "view":
            report = build_report(args.run) if args.run else plan_report(compile_plan(args.workspace))
            result = snapshot(report, args.output) if args.output else serve(report, args.port,
                workspace=None if args.run else args.workspace, run_directory=args.run)
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
