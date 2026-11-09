"""Check source and built artifacts for local-only research and history files."""
from pathlib import Path
import argparse
import subprocess
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_PARTS = {"local-reference", "archive", "setup", "trials", "results", "runs", "plans",
                 "comparisons", "data", "__pycache__", ".venv", "node_modules", ".git"}
PRIVATE_FILES = {"CODE_PROVENANCE_AUDIT.md", "provenance_audit.json", "RELATED_WORK_REVIEW.md",
                 "REVIEW.md", "PLAN.md", "idea_flow.md", "private_splits.json", "TEAMKNITT_FOUNDATIONS.md",
                 "priors.py", "prior_math.py", "prior_protocol.schema.json", "BAYESIAN_PRIORS.md",
                 "bayesian.yaml", "prior-elicitation.yaml"}


def private_path(name):
    path = Path(name)
    return (bool(PRIVATE_PARTS.intersection(path.parts)) or path.name in PRIVATE_FILES
            or any(part.casefold().startswith(("foundations", "fundations")) for part in path.parts)
            or path.name.startswith(".env") and path.name != ".env.example"
            or path.suffix in {".pyc", ".pyo", ".bundle"})


def check_source():
    paths = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT)
    violations = []
    for name in set(paths.decode().split("\0")) - {""}:
        path = ROOT / name
        if path.exists() and (private_path(name) or path.is_symlink()):
            violations.append(name)
    return sorted(violations)


def check_artifact(path):
    violations = []
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            for name in names:
                # Reject every unexpected package namespace, including stale pre-rename files.
                if "/" in name and not name.split("/", 1)[0].endswith(".dist-info") and not name.endswith("/"):
                    source = ROOT / "src" / name
                    if name.split("/", 1)[0] != "teamknitt":
                        violations.append(name + ": foreign package namespace")
                    if not source.is_file() or source.is_symlink():
                        violations.append(name + ": not in current package source")
                    elif source.read_bytes() != archive.read(name):
                        violations.append(name + ": differs from current package source")
    elif path.name.endswith(".tar.gz"):
        with tarfile.open(path) as archive:
            names = archive.getnames()
    else:
        raise ValueError("Choose a wheel or source tar.gz archive.")
    violations.extend(name for name in names if private_path(name))
    for legal in ("LICENSE", "LICENSING.md"):
        if not any(Path(name).name == legal for name in names):
            violations.append("missing " + legal)
    return violations


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", type=Path)
    args = parser.parse_args()
    violations = check_source()
    if args.artifacts:
        found = 0
        for path in sorted(args.artifacts.iterdir()):
            if path.suffix == ".whl" or path.name.endswith(".tar.gz"):
                found += 1
                violations.extend(str(path) + ": " + name for name in check_artifact(path))
        if not found:
            raise SystemExit("No wheel or source archives found in the supplied artifact directory.")
    if violations:
        raise SystemExit("Local-only or invalid release paths:\n" + "\n".join(violations))
    print("Public source and supplied artifacts contain no local-only paths.")


if __name__ == "__main__":
    main()
