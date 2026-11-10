"""Explicit, local workspace name migration. No model calls or statistical conversion."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from uuid import uuid4

from .engine.config import ConfigurationError, parse_yaml
from .compat import normalize_team_config


def migrate(workspace: Path, *, apply=False):
    root = workspace.resolve()
    if not root.is_dir():
        raise ConfigurationError("Choose an existing workspace.")
    lock_path = root / ".run.lock"
    if lock_path.is_symlink():
        raise ConfigurationError("The workspace run lock cannot be a symlink.")
    # Compilation is read-only and rejects unsupported statistical choices before any write.
    team = root / "team.yaml"
    if team.is_symlink():
        raise ConfigurationError("Migration requires a regular team.yaml.")
    if team.is_file():
        from .config import compile_plan
        compile_plan(root)
    else:
        from .engine.study import load_study, plans
        plans(root, load_study(root), workspace=root)
    changes = []
    if team.is_file():
        old = team.read_bytes()
        original = parse_yaml(old.decode("utf-8"))
        normalized = normalize_team_config(original)
        if normalized != original:
            changes.append(("team.yaml", "team.yaml", old, (json.dumps(normalized, indent=2) + "\n").encode()))
    for name in ("lab.py", "engine.py"):
        path = root / name
        if path.is_symlink():
            raise ConfigurationError("Migration cannot overwrite a symlink launcher.")
        if not path.is_file():
            continue
        old = path.read_bytes()
        text = old.decode("utf-8")
        marker = "from labtune.cli import main"
        if marker in text:
            target = "engine.py"
            if name != target and (root / target).exists():
                raise ConfigurationError("Both old and new launchers exist; resolve that conflict explicitly before migration.")
            replacement = text.replace(marker, "from teamknitt.engine.cli import main").replace("lab.py", "engine.py")
            changes.append((name, target, old, replacement.encode()))
    result = {"status": "migration_draft_only", "changes": [{"source": a, "destination": b,
               "before_sha256": hashlib.sha256(old).hexdigest(), "after_sha256": hashlib.sha256(new).hexdigest()}
               for a, b, old, new in changes], "api_calls": 0, "models_or_budgets_changed": False,
              "credentials_or_brief_changed": False,
              "notice": "No statistical choice is converted. Saved records retain their original identities; inspect legacy runs by explicit path."}
    if not apply:
        return result
    import fcntl
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ConfigurationError("A run owns this workspace; migration must wait.") from None
        for source, destination, before, _ in changes:
            if (root / source).is_symlink() or (root / source).read_bytes() != before:
                raise ConfigurationError("Workspace files changed after review; create a new migration draft.")
            if source != destination and ((root / destination).exists() or (root / destination).is_symlink()):
                raise ConfigurationError("The new launcher path now exists; nothing was overwritten.")
        if not changes:
            return {**result, "status": "workspace_already_current"}
        setup = root / "setup"
        parent = setup / "teamknitt-migrations"
        if setup.is_symlink() or parent.is_symlink():
            raise ConfigurationError("Migration backups must remain inside the workspace.")
        backup = parent / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid4().hex[:8])
        backup.mkdir(parents=True, mode=0o700)
        for source, _, before, _ in changes:
            fd = os.open(backup / source, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(before)
        fd = os.open(backup / "manifest.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as stream:
            json.dump(result, stream, indent=2)
        for source, destination, _, content in changes:
            temporary = root / (".migration-" + uuid4().hex + ".tmp")
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(content)
            os.replace(temporary, root / destination)
            if source != destination:
                (root / source).unlink()
        return {**result, "status": "workspace_migrated", "backup": str(backup)}
