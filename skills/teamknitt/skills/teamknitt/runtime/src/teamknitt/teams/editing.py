"""Explicit application with private backups, the shared lock and rollback on write failure."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from uuid import uuid4

from ..engine.config import ConfigurationError
from .config import checked_file, compile_collection, read_config, validate
from .runtime import _lock


def persist(workspace, updates, *, baseline):
    root = Path(workspace).resolve()
    with _lock(root):
        originals = {name: checked_file(root, name).read_bytes() for name in updates}
        if any(hashlib.sha256(originals[name]).hexdigest() != baseline[name] for name in updates):
            raise ConfigurationError('Configuration changed during review; preview it again before applying.')
        if (root / 'setup').is_symlink():
            raise ConfigurationError('Configuration backup storage cannot be a symlink.')
        folder = root / 'setup/team-collection-backups'
        if folder.is_symlink():
            raise ConfigurationError('Configuration backup storage cannot be a symlink.')
        folder.mkdir(parents=True, exist_ok=True, mode=0o700)
        backup = folder / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid4().hex + '.json')
        fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as stream:
            json.dump({k: v.decode('utf-8') for k,v in originals.items()}, stream, indent=2)
        written = []
        try:
            for name, value in updates.items():
                path = checked_file(root, name)
                temporary = path.with_name('.collection-' + uuid4().hex + '.tmp')
                fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                    json.dump(value, stream, indent=2, allow_nan=False);stream.write('\n')
                os.replace(temporary, path)
                written.append(name)
        except BaseException:
            for name in written:
                (root / name).write_bytes(originals[name])
            raise
    return str(backup)


def baseline(workspace, names):
    return {name: hashlib.sha256(checked_file(workspace, name).read_bytes()).hexdigest() for name in names}


def connection_draft(workspace, *, profile=None, source=None, target=None, reciprocal=False, all_links=False, remove=False, words=None):
    c = validate(read_config(workspace))
    policy = c['communication']
    if profile is not None: policy['profile'] = profile
    if words is not None: policy['max_read_words'] = words
    pairs = {(r['source'], r['target']) for r in policy['links']}
    if (source is None) != (target is None):
        raise ConfigurationError('A directed inter-team route needs both source and target.')
    if all_links:
        if source or target or remove:
            raise ConfigurationError('Choose all-to-all or one directed pair, not both.')
        pairs = {(a['id'],b['id']) for a in c['teams'] for b in c['teams'] if a['id'] != b['id']}
    elif source is not None:
        changes = {(source,target)} | ({(target,source)} if reciprocal else set())
        pairs = pairs - changes if remove else pairs | changes
    elif remove or reciprocal:
        raise ConfigurationError('Route removal/reciprocity needs a directed pair.')
    if policy['profile'] == 'none':
        if source or target or all_links:
            raise ConfigurationError('Choose an enabled sharing profile when adding routes.')
        pairs = set()
    policy['links'] = [{'source':a,'target':b} for a,b in sorted(pairs)]
    p = compile_collection(workspace, c)
    return c, p


def persist_clone(workspace, new_id, config, raw_team, raw_study, *, baseline):
    root = Path(workspace).resolve()
    with _lock(root):
        if any(hashlib.sha256(checked_file(root, name).read_bytes()).hexdigest() != expected for name,expected in baseline.items()):
            raise ConfigurationError('Configuration changed during review; preview the clone again.')
        if (root / 'teams').is_symlink():
            raise ConfigurationError('Team configuration directories cannot be symlinks.')
        directory = root / 'teams' / new_id
        if directory.exists() or directory.is_symlink():
            raise ConfigurationError('The new team directory must not already exist.')
        if (root / 'setup').is_symlink() or (root / 'setup/team-collection-backups').is_symlink():
            raise ConfigurationError('Backup storage cannot be a symlink.')
        backups = root / 'setup/team-collection-backups'
        backups.mkdir(parents=True,exist_ok=True,mode=0o700)
        backup = backups / (uuid4().hex + '.json')
        fd = os.open(backup,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w') as stream:
            json.dump({'teams.yaml':(root/'teams.yaml').read_text(),'new_team_directory':'teams/'+new_id},stream,indent=2)
        directory.mkdir(mode=0o700)
        written = []
        temporary = root / ('.collection-'+uuid4().hex+'.tmp')
        try:
            for filename,value in [('team.yaml',raw_team),('study.yaml',raw_study)]:
                path = directory / filename
                fd = os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
                with os.fdopen(fd,'w') as stream:json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')
                written.append(path)
            compile_collection(root,config)
            fd = os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,'w') as stream:json.dump(config,stream,indent=2,allow_nan=False);stream.write('\n')
            os.replace(temporary,root/'teams.yaml')
        except BaseException:
            if temporary.exists():temporary.unlink()
            for path in written:path.unlink()
            directory.rmdir()
            raise
    return str(backup)
