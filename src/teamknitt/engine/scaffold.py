"""Create independent user workspaces from package resources, without model calls."""
from __future__ import annotations

from importlib.resources import files
import json
import os
from pathlib import Path
import secrets
import tempfile

from .config import ConfigurationError, parse_yaml


WORKSPACE_IGNORE = """__pycache__/
*.py[cod]
.venv/
.env
.env.*
!.env.example
mission/memory/private_splits.json
plans/
setup/
trials/
comparisons/
results/
data/
.DS_Store
"""
WRAPPER = """from pathlib import Path
import sys
from teamknitt.engine.cli import main

if __name__ == "__main__":
    root = str(Path(__file__).resolve().parent)
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python engine.py prepare|doctor|qualify|run|compare|visualize [options]")
    raise SystemExit(main(["--project", root, "study", sys.argv[1],
                          "--workspace", root, *sys.argv[2:]]))
"""


def _copy_tree(source, destination):
    destination.mkdir(parents=True, exist_ok=True)
    for child in source.iterdir():
        target = destination / child.name
        if child.is_dir():
            _copy_tree(child, target)
        else:
            target.write_bytes(child.read_bytes())


def _private_panels(path):
    seen = set()
    panels = {}
    for phase in ("development", "confirmation"):
        panels[phase] = {}
        for kind, count in (("calibration", 200), ("null", 100), ("fault", 100)):
            values = []
            while len(values) < count:
                seed = secrets.randbits(63)
                if seed not in seen:
                    seen.add(seed)
                    values.append(seed)
            panels[phase][kind] = values
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(panels, handle, indent=2)
        handle.write("\n")


def init_workspace(destination: Path, template: str = "text", decision_backend: str | None = None) -> dict:
    if template not in {"text", "memory", "scientist", "multi-lab"}:
        raise ConfigurationError("Unknown starter template.")
    if decision_backend not in {None, "llm_only", "chat_completions", "typed"}:
        raise ConfigurationError("Choose llm_only, chat_completions or typed for decision routing.")
    destination = destination.expanduser().absolute()
    if destination.exists() or destination.is_symlink():
        raise ConfigurationError("Choose a new workspace path; init never overwrites existing files.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    starter = files("teamknitt.engine.resources").joinpath("starter")
    with tempfile.TemporaryDirectory(prefix=".teamknitt-init-", dir=destination.parent) as temporary:
        stage = Path(temporary) / "workspace"
        _copy_tree(starter.joinpath("project"), stage)
        _copy_tree(starter.joinpath(template), stage)
        if decision_backend is not None:
            study = parse_yaml((stage / "study.yaml").read_text())
            settings = study["base_overrides"].setdefault("decisions", {})
            settings.update(mode="llm_only" if decision_backend == "llm_only" else "selected_active",
                            specialist=None if decision_backend == "llm_only" else "specialist",
                            allowed_specs=["semantic_choice.v1"])
            if decision_backend != "llm_only":
                study["decision_providers"] = {"specialist": {
                    "adapter": decision_backend, "base_url": "https://decisions.example.invalid/v1",
                    "endpoint": "/assess" if decision_backend == "typed" else "/chat/completions",
                    "model": "YOUR_DECISION_MODEL_ID", "api_key_env": "TEAMKNITT_DECISION_API_KEY",
                    "env_file": ".env", "timeout_seconds": 90, "max_parallel_requests": 2}}
            (stage / "study.yaml").write_text(json.dumps(study, indent=2) + "\n")
        (stage / ".gitignore").write_text(WORKSPACE_IGNORE, encoding="utf-8")
        (stage / ".env.example").write_text("TEAMKNITT_API_KEY=replace-me\n# Optional separate decision endpoint:\nTEAMKNITT_DECISION_API_KEY=replace-me\n", encoding="utf-8")
        (stage / "engine.py").write_text(WRAPPER, encoding="utf-8")
        if template == "memory":
            _private_panels(stage / "mission/memory/private_splits.json")
        (stage / "README.md").write_text(
            "# Your teamknitt workspace\n\n"
            "Edit study.yaml to choose models, designs, sharing, statistics and budgets.\n"
            "Then run python engine.py prepare (no key or model call).\n"
            "Choose your provider URL, endpoint and model in study.yaml before any live run.\n"
            "Copy .env.example to .env and set the configured private key locally.\n"
            "python engine.py doctor is local; doctor --live makes metered connectivity calls.\n"
            "Read mission/problem.md or mission/memory/problem.md before any run.\n"
            "The memory template requires the memory extra and macOS sandbox-exec; run\n"
            "python engine.py qualify before python engine.py run --variant memory-single.\n"
            "The text template proposes ideas only; replace AWAITING_USER_PROBLEM first.\n"
            "Use python engine.py run --variant single for the text template.\n"
            "Use python engine.py run --variant scientist-medium --sequences 3 for a single\n"
            "scientist continuing three sequences. Select scientist-low or scientist-persistent\n"
            "for other effort levels; persistent also accepts --effort-mode budget.\n"
            "All sequences share the chosen study budgets; initialization starts no research.\n"
            "For the multi-lab template, edit multi_lab in study.yaml and run\n"
            "python engine.py prepare --multi-lab, then run --multi-lab --sequences 2.\n"
            "Select each lab's variant, inter-lab sharing and conference/symposium settings.\n"
            "python engine.py visualize --multi-lab shows the lab and meeting sequence.\n"
            "Use python engine.py visualize --variant single (or memory-single) to view\n"
            "the process locally with two read-only agents; no model calls are made.\n"
            "Keep private seeds, credentials, generated trials and results out of Git.\n\n"
            "teamknitt copyright holder and licensor: Pioneertown B.V. Author: Goran Mitevski.\n"
            "teamknitt material is licensed for independent noncommercial academic research\n"
            "at qualifying public or nonprofit educational institutions in World Bank low-income\n"
            "or lower-middle-income economies, and by their authorized users, under the\n"
            "Labtune Academic Research License 2.0.\n"
            "Company labs, corporate research proxies and commissioned company work are excluded.\n"
            "Company donations must be unrestricted, without control or privileged results/IP rights.\n"
            "Other use, including by institutions in upper-middle-income or high-income economies,\n"
            "requires separate written permission before use. Contact Goran Mitevski:\n"
            "goran@pioneertown.ai.\n"
            "Read LICENSE and LICENSING.md;\n"
            "your independent research data and outputs are not relicensed merely by using teamknitt.\n",
            encoding="utf-8")
        # Exclusive destination creation: a concurrent creator cannot be overwritten.
        destination.mkdir()
        try:
            for child in stage.iterdir():
                child.rename(destination / child.name)
        except BaseException:
            # Keep partial output for diagnosis; a retry must use a new destination.
            raise
    return {"status": "workspace_created", "template": template,
            "workspace": str(destination), "project": str(destination),
            "api_calls": 0, "research_started": False,
            "private_seed_file_created": template == "memory"}
