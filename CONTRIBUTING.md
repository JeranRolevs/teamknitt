# Contributing

## Permission before code or documentation changes

The **Teamknitt Noncommercial Licence 1.0** does **not** grant permission to redistribute
or modify the software or make derivative works, even for noncommercial purposes. Public
source access, a fork/PR workflow and this guide do not add permissions. Before preparing or
sharing software patches, modified copies or derivative contributions, obtain separate written
permission from **Pioneertown B.V.**, through **Goran Mitevski** at
[goran@pioneertown.ai](mailto:goran@pioneertown.ai), unless you have independent legal rights.
An issue report or discussion is not permission. No copyright assignment or additional licence
is implied by these instructions. See [LICENSE](LICENSE) and [LICENSING.md](LICENSING.md).

The following development/release instructions are for the licensor and separately authorized
contributors. Preserve existing copyright, author and dependency notices in authorized work.

## Authorized development — offline

Work from this repository root, the independent teamknitt Python package. Python 3.11+ is required.

```bash
python3 -m pip install -e '.[memory,diagrams]'
python3 tools/sync_starter.py --check
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m unittest discover -s examples/memory_retention/tests -v
python3 diagrams/render_flowcharts.py
python3 tools/check_release.py
```

Edit canonical examples and templates, then run sync_starter.py without --check. Its output
under src/teamknitt/engine/resources/starter/ is generated package data. Test a built wheel from outside
the checkout; editable-install success alone does not establish a portable release.

Do not copy the legacy parent implementation, upstream source/prompts/templates, or local
private research data. Keep failures and provenance in user workspaces. No real API calls in
tests, CI, package builds, init, prepare, check or plan. A local doctor checks credentials;
doctor --live and study run are explicit metered actions.

Lab styles and communication remain user choices. Compare them with repeated matched-budget
runs; one smoke trial cannot establish a winner. Any contribution/release permissions and
terms must be agreed with the licensor separately; the public licence is not a modification
or redistribution grant. Retain applicable notices and identify authorized changes.

For a release, build wheels and a source distribution and run
python3 tools/check_release.py --artifacts dist. Keep ignored local archives and audit/review
records out of both Git and artifacts. Preserve dependency licence obligations. All starter
provider URLs and model IDs remain placeholders; live service selection belongs to the user.


## teamknitt product layer

Use teamknitt for user-directed task/idea/goal configuration and monitoring, with teamknitt as
the engine and aesthetic foundation. Preserve explicit count/topology/sharing, model, tool,
statistics, delegation and budget choices; no automated organization improvement or hidden
allowance. The distributed-problem-solving framework and optional dynamical-systems observation
lenses must retain their interpretation limits. Drafting is not application; running is not
goal achievement. Test topology permissions at runtime, private artifacts and backups,
non-mutating viewer APIs, live metadata, the renamed wheel outside the checkout and retained
engine/advanced/probe compatibility. Synchronize public starters and canonical layouts with
tools/sync_starter.py; architecture diagrams use diagrams/specs.py. Preserve both legal texts
and credits; wider task capability does not widen licensing permission.
