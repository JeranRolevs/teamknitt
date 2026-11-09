"""Keep wheel starter resources identical to the public checkout templates."""
from pathlib import Path
import argparse
import shutil
import sys

PROJECT = Path(__file__).resolve().parents[1]
TARGET = PROJECT / "src/teamknitt/engine/resources/starter"


def desired():
    output = {}
    for name in ("LICENSE", "LICENSING.md", "PROVENANCE.md"):
        output["project/" + name] = (PROJECT / name).read_bytes()
    for folder in ("lab_designs", "configs", "prompts", "templates"):
        for source in (PROJECT / folder).rglob("*"):
            if source.is_file() and source.suffix in {".md", ".yaml", ".json"}:
                if folder == "configs" and source.name != "lab.yaml":
                    continue
                output["project/" + source.relative_to(PROJECT).as_posix()] = source.read_bytes()
    for name in ("SINGLE_SCIENTIST.md", "MULTI_LAB.md", "PROVIDERS.md", "DECISION_PROVIDERS.md", "MIGRATION.md", "TEAMKNITT.md"):
        guide = PROJECT / "docs" / name
        if guide.is_file():
            output["project/docs/" + name] = guide.read_bytes()
    for name, example in (("text", "text_workflow"), ("memory", "memory_retention"), ("scientist", "single_scientist"), ("multi-lab", "multi_lab")):
        for source in (PROJECT / "examples" / example).rglob("*"):
            if (source.is_file() and source.suffix in {".py", ".yaml", ".md", ".json"}
                    and "__pycache__" not in source.parts
                    and source.name != "private_splits.json"
                    and "tests" not in source.relative_to(PROJECT / "examples" / example).parts):
                output[name + "/" + source.relative_to(PROJECT / "examples" / example).as_posix()] = source.read_bytes()
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = desired()
    actual = {p.relative_to(TARGET).as_posix(): p.read_bytes()
              for p in TARGET.rglob("*") if p.is_file() and "__pycache__" not in p.parts} if TARGET.exists() else {}
    changed = sorted(k for k in expected.keys() | actual.keys() if expected.get(k) != actual.get(k))
    if args.check:
        if changed:
            print("Starter resources need synchronization: " + ", ".join(changed), file=sys.stderr)
            return 1
    else:
        # This directory contains generated resources only.
        if TARGET.exists():
            shutil.rmtree(TARGET)
        for relative, data in expected.items():
            target = TARGET / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    # Export runtime topology positions from the canonical diagram specification.
    import importlib.util
    import json
    spec = importlib.util.spec_from_file_location("teamknitt_diagrams", PROJECT / "diagrams/specs.py")
    diagram_specs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(diagram_specs)
    layouts = {kind: {str(n): diagram_specs.team_topology_layout(kind, n) for n in range(1, 17)}
               for kind in diagram_specs.TEAM_TOPOLOGIES}
    geometry = (json.dumps(layouts, indent=2) + "\n").encode()
    geometry_path = PROJECT / "src/teamknitt/resources/topology-layouts.json"
    if args.check and (not geometry_path.is_file() or geometry_path.read_bytes() != geometry):
        print("Topology layouts need synchronization from diagrams/specs.py", file=sys.stderr)
        return 1
    if not args.check:
        geometry_path.write_bytes(geometry)
    catalog = (json.dumps(diagram_specs.TEAM_TOPOLOGIES, indent=2) + "\n").encode()
    catalog_path = PROJECT / "src/teamknitt/resources/topology-catalog.json"
    if args.check and (not catalog_path.is_file() or catalog_path.read_bytes() != catalog):
        print("Topology catalog needs synchronization from diagrams/specs.py", file=sys.stderr)
        return 1
    if not args.check:
        catalog_path.write_bytes(catalog)
    schema_path = PROJECT / "src/teamknitt/resources/team.schema.json"
    schema = json.loads(schema_path.read_text())
    kinds = list(diagram_specs.TEAM_TOPOLOGIES)
    if args.check and schema["properties"]["team"]["properties"]["topology"]["enum"] != kinds:
        print("Topology schema needs synchronization from diagrams/specs.py", file=sys.stderr)
        return 1
    if not args.check:
        schema["properties"]["team"]["properties"]["topology"]["enum"] = kinds
        schema_path.write_text(json.dumps(schema, indent=2) + "\n")
    # Teamknitt task and advanced research starters are authoritative public examples.
    team_target = PROJECT / "src/teamknitt/resources"
    team_sources = {"team.yaml": PROJECT / "examples/task_team/team.yaml",
                    "WORKSPACE.md": PROJECT / "examples/task_team/README.md",
                    "research-team.yaml": PROJECT / "examples/research_cognition/team.yaml",
                    "RESEARCH_WORKSPACE.md": PROJECT / "examples/research_cognition/README.md",
                    "probe.yaml": PROJECT / "examples/teammate_probes/team.yaml",
                    "PROBES_WORKSPACE.md": PROJECT / "examples/teammate_probes/README.md"}
    for folder, example in (("task-starter", "task_team"), ("research-starter", "research_cognition")):
        for source in (PROJECT / "examples" / example).rglob("*"):
            if source.is_file() and source.name not in {"README.md", "team.yaml"} and source.suffix in {".md", ".yaml"}:
                team_sources[folder + "/" + source.relative_to(PROJECT / "examples" / example).as_posix()] = source
    if not args.check:
        for folder in ("task-starter", "research-starter", "cognition-starter"):
            if (team_target / folder).exists():
                shutil.rmtree(team_target / folder)
    for name, source in team_sources.items():
        target = team_target / name
        data = source.read_bytes()
        if args.check and (not target.is_file() or target.read_bytes() != data):
            print("Teamknitt starter needs synchronization: " + name, file=sys.stderr)
            return 1
        if not args.check:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    print(f"Starter resources: {len(expected)} engine files + {len(team_sources)} team files; synchronized.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
