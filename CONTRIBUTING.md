# Contributing

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
runs; one smoke trial cannot establish a winner. Contributions must be offered under the
[Labtune Academic Research License 2.0](LICENSE); retain applicable notices and identify changes.
Free permission requires an eligible academic institution in a World Bank low-income or
lower-middle-income economy. For other use, request separate written permission through
Goran Mitevski at [goran@pioneertown.ai](mailto:goran@pioneertown.ai); see [licensing](LICENSING.md).

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
