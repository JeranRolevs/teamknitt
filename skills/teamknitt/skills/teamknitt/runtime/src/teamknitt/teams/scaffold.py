"""Native multi-team starter; no remote skills, templates or provider calls."""
from copy import deepcopy
import json
from pathlib import Path
import re

from ..builder import make_configuration
from ..config import resource
from ..scaffold import init as init_team
from ..engine.config import ConfigurationError, parse_yaml
from .config import compile_collection

WRAPPER = '''from pathlib import Path
import sys
from teamknitt.teams.cli import main
if __name__ == "__main__":
    command, *args = sys.argv[1:] or ["check"]
    if command in {"check", "plan", "prepare", "demo", "run", "view", "configure", "connect", "schedule", "add", "remove"}:
        args = ["--workspace", str(Path(__file__).resolve().parent), *args]
    raise SystemExit(main([command, *args]))
'''


def init(destination, *, ids=('alpha', 'beta', 'gamma'), count=3, topology='fully_connected', sharing='high', purpose='task', goal=None,
         request_cap=24, wall_seconds=600):
    ids = list(ids)
    if not 1 <= len(ids) <= 8 or len(set(ids)) != len(ids) or any(re.fullmatch(r'[a-z][a-z0-9_-]{0,31}', t) is None for t in ids):
        raise ConfigurationError('Choose 1–8 unique lowercase, path-safe team IDs.')
    if type(request_cap) is not int or not 1 <= request_cap <= 100000 or type(wall_seconds) is not int or not 1 <= wall_seconds <= 86400:
        raise ConfigurationError('Choose bounded total request and wall-time caps.')
    result = init_team(destination, count=count, topology=topology, communication=sharing, purpose=purpose, goal=goal)
    root = Path(result['workspace'])
    base_study = parse_yaml((root / 'study.yaml').read_text())
    entries = []
    for team_id in ids:
        folder = root / 'teams' / team_id
        folder.mkdir(parents=True)
        c = make_configuration(count=count, topology=topology, communication=sharing, purpose=purpose, name=team_id)
        (folder / 'team.yaml').write_text(json.dumps(c, indent=2) + '\n')
        settings = deepcopy(base_study)
        settings['name'] = team_id
        (folder / 'study.yaml').write_text(json.dumps(settings, indent=2) + '\n')
        entries.append({'id': team_id, 'name': team_id, 'configuration_file': f'teams/{team_id}/team.yaml',
            'study_file': f'teams/{team_id}/study.yaml', 'exporter': 'member.1',
            'style': {'label': 'Native task-team configuration', 'file': None, 'authorship': None, 'references': []}})
    c = {'schema_version': 1, 'name': 'Multiple teams', 'task': {'brief_file': 'mission/task.md', 'deliverable': 'Separate team contributions to the same task, for user review.'},
         'budget': {'max_llm_calls': request_cap, 'max_wall_seconds': wall_seconds},
         'resources': {'max_active_agents': 6, 'max_llm_requests': 2},
         'communication': {'profile': 'none', 'max_read_words': 400, 'links': []}, 'teams': entries}
    (root / 'teams.yaml').write_text(json.dumps(c, indent=2) + '\n')
    (root / 'team.yaml').unlink()  # This fresh workspace is a collection, never an ambiguous single-team run.
    (root / 'study.yaml').unlink()
    (root / 'team.py').write_text(WRAPPER)
    (root / '.gitignore').write_text((root / '.gitignore').read_text() + '\n/styles/\n/mission/feedback*.md\n')
    (root / 'README.md').write_bytes(resource('MULTI_TEAM_WORKSPACE.md').read_bytes())
    compile_collection(root)
    return {**result, 'template': 'multi-team', 'teams': ids, 'request_cap_all_teams': request_cap, 'communication': 'none', 'api_calls': 0}
