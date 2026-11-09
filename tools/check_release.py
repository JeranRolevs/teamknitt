"""Check public paths, current package bytes, legal copies and release metadata."""
from pathlib import Path
from email.parser import BytesParser
import argparse
import subprocess
import tarfile
import tomllib
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
    violations, legal_copies, metadata = [], {}, {}
    legal_names = {"LICENSE", "LICENSING.md"}
    def capture(name, body):
        parts = Path(name).parts
        if Path(name).name in legal_names and (
            len(parts) == (1 if path.suffix == ".whl" else 2)
            or name.endswith("/engine/resources/starter/project/" + Path(name).name)
            or len(parts) == 3 and parts[0].endswith(".dist-info") and parts[1] == "licenses"
        ):
            legal_copies[name] = body
        if (Path(name).name == "METADATA" and Path(name).parent.name.endswith(".dist-info")) or Path(name).name == "PKG-INFO":
            metadata[name] = body
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            for name in names:
                if Path(name).name in legal_names | {"METADATA", "PKG-INFO"}:
                    capture(name, archive.read(name))
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
            for member in archive.getmembers():
                if member.isfile() and Path(member.name).name in legal_names | {"PKG-INFO"}:
                    capture(member.name, archive.extractfile(member).read())
    else:
        raise ValueError("Choose a wheel or source tar.gz archive.")
    violations.extend(name for name in names if private_path(name))
    if len(names) != len(set(names)):
        violations.append("duplicate archive entries")
    for legal in sorted(legal_names):
        copies = {name: body for name, body in legal_copies.items() if Path(name).name == legal}
        if not copies:
            violations.append("missing " + legal)
        for name, body in copies.items():
            if body != (ROOT / legal).read_bytes():
                violations.append(name + ": differs from current " + legal)
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    if not metadata:
        violations.append("missing package metadata")
    for name, body in metadata.items():
        headers = BytesParser().parsebytes(body, headersonly=True)
        for field, key in (("Name", "name"), ("Version", "version"), ("License-Expression", "license")):
            if headers.get_all(field) != [project[key]]:
                violations.append(name + ": incorrect " + field)
        if set(headers.get_all("License-File", [])) != set(project["license-files"]):
            violations.append(name + ": incorrect License-File")
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
    print("Public source and supplied artifacts pass privacy, source, legal-copy and metadata checks.")


if __name__ == "__main__":
    main()
