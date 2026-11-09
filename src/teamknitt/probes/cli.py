"""Teamknitt CLI: local preparation by default, explicitly authorized live execution."""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys

from teamknitt.engine.config import ConfigurationError
from teamknitt.engine.providers.http import ProviderError
from teamknitt.engine.study import StudyError

from teamknitt import __version__
from .config import load, plan
from .observatory import serve, snapshot
from .reporting import load_run, report
from .runtime import run
from .scaffold import init
from .scenarios import catalogue


def main(argv=None):
    parser = argparse.ArgumentParser(prog="teamknitt probes", description="Optional synthetic teammate probes; separate from the distributed-problem-solving configuration layer.")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    start = commands.add_parser("init", help="Create a standalone team workspace with no model calls")
    start.add_argument("destination", type=Path)
    commands.add_parser("tasks", help="Describe the eight original synthetic task families")
    for name in ("check", "plan", "demo", "run"):
        sub = commands.add_parser(name, help={"check": "Validate all explicit team settings locally", "plan": "Inspect controls and request upper bound without reading credentials",
                                             "demo": "Run a transparent deterministic fixture, not a model evaluation", "run": "Run selected provider models only with explicit authorization"}[name])
        sub.add_argument("--workspace", type=Path, default=Path.cwd())
        if name == "demo":
            sub.add_argument("--policy", choices=("coordinated", "fragile"), default="coordinated")
        if name == "run":
            sub.add_argument("--live", action="store_true", help="Explicitly authorize metered provider calls")
            sub.add_argument("--approve-requests", type=int, help="Must equal budget.max_requests in team.yaml")
    summary = commands.add_parser("report", help="Recompute a capability-conditioned report locally")
    summary.add_argument("run", type=Path, help="Saved run directory or run.json")
    view = commands.add_parser("view", help="View a saved run; read-only and no provider calls")
    view.add_argument("run", type=Path, help="Saved run directory or run.json")
    view.add_argument("--output", type=Path, help="Create a new private standalone HTML file instead of serving")
    view.add_argument("--port", type=int, default=8766)
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            result = init(args.destination)
        elif args.command == "tasks":
            result = {"tasks": catalogue(), "api_calls": 0}
        elif args.command in {"view", "report"}:
            summary = report(load_run(args.run))
            result = summary if args.command == "report" else snapshot(summary, args.output) if args.output else serve(summary, args.port)
        else:
            config = load(args.workspace)
            if args.command in {"check", "plan"}:
                compiled = plan(config)
                result = compiled if args.command == "plan" else {
                    "status": "team_configuration_valid", "configuration_sha256": compiled["configuration_sha256"],
                    "task_count": compiled["task_count"], "episode_count": compiled["episode_count"],
                    "provider_request_upper_bound": compiled["provider_request_upper_bound"],
                    "budget_covers_request_upper_bound": compiled["budget_covers_request_upper_bound"],
                    "api_calls": 0, "research_started": False}
            elif args.command == "run":
                if not args.live:
                    raise ConfigurationError("run requires --live and --approve-requests; use demo for an offline fixture.")
                result = asyncio.run(run(args.workspace, config, live=True, approve_requests=args.approve_requests))
            else:
                result = asyncio.run(run(args.workspace, config, policy=args.policy))
        print(json.dumps(result, indent=2, allow_nan=False))
        return 2 if result.get("status") == "incomplete" else 0
    except (ConfigurationError, ProviderError, StudyError, OSError, ValueError) as error:
        print(f"teamknitt error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
