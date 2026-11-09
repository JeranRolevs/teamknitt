"""Create a user-task team workspace with teamknitt as the engine, not the product UI."""
from pathlib import Path
import json
from teamknitt.engine.config import ConfigurationError
from teamknitt.engine.scaffold import init_workspace
from .config import resource
from .builder import make_configuration

WRAPPER = '''from pathlib import Path
import sys
from teamknitt.cli import main

if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python team.py check|plan|prepare|configure|demo|run [options]")
    raise SystemExit(main([sys.argv[1], "--workspace", str(Path(__file__).resolve().parent), *sys.argv[2:]]))
'''


def _copy(source, destination):
    destination.mkdir(parents=True, exist_ok=True)
    for child in source.iterdir():
        if child.is_dir():
            _copy(child, destination / child.name)
        else:
            (destination / child.name).write_bytes(child.read_bytes())


def init(destination: Path, *, template="task", topology="fully_connected", count=3, communication="high", purpose="brainstorm", goal=None):
    if template not in {"task", "research"}:
        raise ConfigurationError("Choose a user-task or advanced research template.")
    if goal is not None and (not isinstance(goal, str) or not goal.strip()):
        raise ConfigurationError("Supply nonempty task/goal text.")
    config = make_configuration(topology=topology, count=count, communication=communication, purpose=purpose) if template == "task" else None
    result = init_workspace(destination)
    root = Path(result["workspace"])
    _copy(resource("task-starter" if template == "task" else "research-starter"), root)
    (root / "team.yaml").write_text(json.dumps(config, indent=2) + "\n" if config else resource("research-team.yaml").read_text())
    (root / "team.py").write_text(WRAPPER)
    (root / "README.md").write_bytes(resource("WORKSPACE.md" if template == "task" else "RESEARCH_WORKSPACE.md").read_bytes())
    (root / ".gitignore").write_text((root / ".gitignore").read_text() + "\nruns/\n*.teamknitt.html\n[Ff]oundations*\n[Ff]undations*\nTEAMKNITT_FOUNDATIONS.md\n")
    if goal is not None:
        if not isinstance(goal, str) or not goal.strip():
            raise ConfigurationError("Supply nonempty task/goal text.")
        path = "mission/task.md" if template == "task" else "mission/problem.md"
        (root / path).write_text(goal.strip() + "\n")
    return {**result, "product": "teamknitt", "template": "user-task-team" if template == "task" else "advanced-research-cognition", "research_started": False, "api_calls": 0}
