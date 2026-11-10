"""Keep the runtime bundled with the teamknitt skill identical to this checkout."""
from pathlib import Path
import argparse
import shutil
import sys

PROJECT = Path(__file__).resolve().parents[1]
TARGET = PROJECT / "skills/teamknitt/skills/teamknitt/runtime"
ROOT_FILES = ("pyproject.toml", "README.md", "LICENSE", "LICENSING.md", "PROVENANCE.md")


def excluded(path):
    name = path.name.lower()
    return ("__pycache__" in path.parts or path.suffix in {".pyc", ".pyo", ".pyd"}
            or name.startswith(("foundations", "fundations")) or name == "teamknitt_foundations.md")


def desired():
    output = {name: (PROJECT / name).read_bytes() for name in ROOT_FILES}
    for source in (PROJECT / "src/teamknitt").rglob("*"):
        if source.is_file() and not excluded(source):
            output[source.relative_to(PROJECT).as_posix()] = source.read_bytes()
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = desired()
    actual = {p.relative_to(TARGET).as_posix(): p.read_bytes()
              for p in TARGET.rglob("*") if p.is_file() and not excluded(p)} if TARGET.exists() else {}
    changed = sorted(k for k in expected.keys() | actual.keys() if expected.get(k) != actual.get(k))
    if args.check:
        if changed:
            print("Skill runtime needs synchronization: " + ", ".join(changed), file=sys.stderr)
            return 1
    else:
        # This directory contains generated copies only.
        if TARGET.exists():
            shutil.rmtree(TARGET)
        for relative, data in expected.items():
            target = TARGET / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    print(f"Skill runtime: {len(expected)} files; synchronized.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
