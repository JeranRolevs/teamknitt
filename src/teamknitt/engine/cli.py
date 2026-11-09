"""Structural plans plus explicit, opt-in provider study commands."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .config import ConfigurationError
from .providers.http import ProviderError
from .planning import PROFILES, STATISTICAL_APPROACHES, catalogue, compile_plan
from .study import StudyError, command as study_command
from .research import ResearchError
from .scaffold import init_workspace
from .visualization import visualize
from .persistence import PERSISTENCE_PASSES, EFFORT_MODES, SEQUENCE_CONTEXTS


def scientist_options(command):
    command.add_argument("--persistence", choices=tuple(PERSISTENCE_PASSES), help="Single-scientist effort level")
    command.add_argument("--sequences", type=int, help="Number of research sequences for a scientist or multi-lab study")
    command.add_argument("--effort-mode", choices=EFFORT_MODES, help="Fixed passes, or persistent work within shared budget allowances")
    command.add_argument("--sequence-context", choices=SEQUENCE_CONTEXTS, help="Continue working context (default), or explicitly reset between sequences")


def scientist_args(args):
    return {key: getattr(args, key, None) for key in ("persistence", "sequences", "effort_mode", "sequence_context")}


def visualization_options(command, *, study=False):
    scientist_options(command)
    if not study:
        command.add_argument("--workspace", type=Path, help="Observe runs in this workspace")
        command.add_argument("--config", default="configs/lab.yaml")
        command.add_argument("--design", help="Select a project-relative design Markdown")
        command.add_argument("--profile", choices=PROFILES)
        command.add_argument("--statistics", choices=STATISTICAL_APPROACHES)
    selection = command.add_mutually_exclusive_group()
    selection.add_argument("--variant", help="Visualize a study variant instead of the base configuration")
    selection.add_argument("--multi-lab", action="store_true", help="Visualize the configured labs, meetings and research sequences")
    command.add_argument("--trial", help="Inspect a saved trial and its recorded setup")
    command.add_argument("--output", type=Path, help="Save a standalone HTML snapshot instead of serving")
    command.add_argument("--port", type=int, default=8765, help="Local viewer port (0 chooses an available port)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="teamknitt engine", description="Create configurable labs, inspect plans, or explicitly run bounded research workflows.")
    parser.add_argument("--project", type=Path, default=Path.cwd(), help="teamknitt project directory")
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="Create a standalone workspace without model calls")
    init.add_argument("destination", type=Path)
    init.add_argument("--template", choices=("text", "memory", "scientist", "multi-lab"), default="text")
    init.add_argument("--decision-backend", choices=("llm_only", "chat_completions", "typed"), help="Choose a decision protocol without making API calls")
    commands.add_parser("designs", help="List validated Markdown designs")
    visualization_options(commands.add_parser("visualize", help="View a lab process using two local, read-only visualization agents"))
    for name, help_text in (("plan", "Compile an inspectable JSON plan"), ("check", "Check configuration and all preset contracts")):
        sub = commands.add_parser(name, help=help_text)
        sub.add_argument("--config", default="configs/lab.yaml")
        if name == "plan":
            scientist_options(sub)
            sub.add_argument("--design", help="Override the project-relative design Markdown")
            sub.add_argument("--profile", choices=PROFILES)
            sub.add_argument("--wisdom", choices=("on", "off"))
            sub.add_argument("--statistics", choices=STATISTICAL_APPROACHES,
                             help="Statistical approach when analysis is needed; no computation during planning")
    study = commands.add_parser("study", help="Explicit provider connection and workflow comparisons")
    operations = study.add_subparsers(dest="operation", required=True)
    for operation in ("prepare", "doctor", "qualify", "run", "compare", "visualize"):
        command = operations.add_parser(operation)
        command.add_argument("--workspace", type=Path, required=True)
        if operation == "doctor":
            command.add_argument("--live", action="store_true", help="Metered generation and selected-specialist probes")
            command.add_argument("--variant", help="Check only this variant and its selected decision backend")
        if operation == "run":
            selection = command.add_mutually_exclusive_group(required=True)
            selection.add_argument("--variant")
            selection.add_argument("--multi-lab", action="store_true", help="Run the configured collection of labs")
            scientist_options(command)
        if operation == "prepare":
            command.add_argument("--multi-lab", action="store_true")
            command.add_argument("--sequences", type=int)
            command.add_argument("--sequence-context", choices=SEQUENCE_CONTEXTS)
        if operation == "visualize":
            visualization_options(command, study=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            result = init_workspace(args.destination, args.template, args.decision_backend)
        elif args.command == "visualize" or (args.command == "study" and args.operation == "visualize"):
            result = visualize(args.project, workspace=args.workspace, variant=args.variant, trial=args.trial,
                               multi_lab=args.multi_lab,
                               output=args.output, port=args.port, config=getattr(args, "config", "configs/lab.yaml"),
                               design=getattr(args, "design", None), profile=getattr(args, "profile", None),
                               statistics=getattr(args, "statistics", None), **scientist_args(args))
        elif args.command == "study":
            result = study_command(args.project, args.workspace, args.operation,
                                   multi_lab=getattr(args, "multi_lab", False),
                                   live=getattr(args, "live", False), variant=getattr(args, "variant", None),
                                   **scientist_args(args))
        elif args.command == "designs":
            result = catalogue(args.project)
        elif args.command == "check":
            rows = catalogue(args.project)
            # Persona overrides belong to the selected design, not every catalogue entry.
            compile_plan(args.project, args.config)
            result = {"status": "structural_checks_passed", "presets": len(rows),
                      "runtime_executed": False, "comparative_experiments_run": False}
        else:
            wisdom = None if args.wisdom is None else args.wisdom == "on"
            result = compile_plan(args.project, args.config, design_file=args.design,
                                  profile=args.profile, wisdom=wisdom, statistical_approach=args.statistics,
                                  **scientist_args(args))
        print(json.dumps(result, indent=2, allow_nan=False))
        if args.command == "study" and result.get("status") in {"credential_missing", "connection_failed", "failed_or_incomplete"}:
            return 2
        return 0
    except (ConfigurationError, StudyError, ResearchError, ProviderError, OSError) as exc:
        print(f"configuration error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
