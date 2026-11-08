"""Portable team workspace, retaining the original Labtune research tools and license."""
from __future__ import annotations

from pathlib import Path

from labtune.scaffold import init_workspace
from .config import resource


WRAPPER = '''from pathlib import Path
import sys
from teamknitt.probes.cli import main

if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python team.py check|plan|demo|run [options]")
    raise SystemExit(main([sys.argv[1], "--workspace", str(Path(__file__).resolve().parent), *sys.argv[2:]]))
'''


def init(destination: Path):
    result = init_workspace(destination)
    root = Path(result["workspace"])
    (root / "team.yaml").write_bytes(resource("team.yaml").read_bytes())
    (root / "team.py").write_text(WRAPPER)
    (root / "README.md").write_bytes(resource("WORKSPACE.md").read_bytes())
    (root / ".gitignore").write_text((root / ".gitignore").read_text() + "\nruns/\n*.teamknitt.html\n")
    with (root / ".env.example").open("a") as stream:
        stream.write("\n# Teamknitt generation endpoint (choose explicitly in team.yaml):\nTEAMKNITT_API_KEY=replace-me\n")
    return {**result, "product": "teamknitt", "template": "team-dynamics", "research_started": False, "api_calls": 0}
