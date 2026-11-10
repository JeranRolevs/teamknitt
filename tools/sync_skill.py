"""Keep the reference guides and legal texts shipped with the teamknitt skill identical to this checkout.

The plugin carries instructions and documents only. The skill installs the teamknitt tool from
this repository at the commit pinned in its SKILL.md.
"""
from pathlib import Path
import argparse
import sys

PROJECT = Path(__file__).resolve().parents[1]
PLUGIN = PROJECT / "skills/teamknitt"
COPIES = {
    "skills/teamknitt/references/TEAMKNITT.md": "docs/TEAMKNITT.md",
    "skills/teamknitt/references/MULTI_TEAM.md": "docs/MULTI_TEAM.md",
    "skills/teamknitt/references/PROVIDERS.md": "docs/PROVIDERS.md",
    "licenses/TEAMKNITT-NONCOMMERCIAL-RESEARCH-LICENCE-2.0.txt": "LICENSE",
    "licenses/LICENSING.md": "LICENSING.md",
    "licenses/PROVENANCE.md": "PROVENANCE.md",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    changed = []
    for target_name, source_name in COPIES.items():
        target, data = PLUGIN / target_name, (PROJECT / source_name).read_bytes()
        if not target.is_file() or target.read_bytes() != data:
            changed.append(target_name)
            if not args.check:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
    if args.check and changed:
        print("Skill documents need synchronization: " + ", ".join(changed), file=sys.stderr)
        return 1
    print(f"Skill documents: {len(COPIES)} files; synchronized.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
