# Provenance

**teamknitt is based on Labtune**, the original work and configuration idea of **Goran Mitevski**.
Copyright holder and licensor: **Pioneertown B.V.**

The retained source baseline is Labtune 0.5.0, commit
`d0f462a28bcc4267f8767316d8c73c3c72201063`, from
<https://github.com/JeranRolevs/labtune>, together with the subsequent teamknitt work in this
repository. The code was adapted from this repository's engine, not an unrelated parent
project, external agent runtime, benchmark implementation or private source collection.

teamknitt now ships and maintains its own execution engine, provider adapters, schemas,
workspaces and monitoring under `teamknitt.engine`. It does not import or require an installed
Labtune package, delegate execution to its CLI, or depend on its development checkout.
Only the `teamknitt` console command and package namespace are distributed.

## Research follow-up

teamknitt follows up **Goran Mitevski’s 2022/2023 thesis research** on distributed teams and
their creative processes. It continues that work through configurable AI-agent teams, work
monitoring and human-directed intervention. This is research lineage, separate from the
software source baseline above; it does not import thesis code, datasets or the full thesis.

Starting with the 0.8.0 development version, teamknitt material offered by Pioneertown B.V.
uses the **Teamknitt Noncommercial Licence 1.0**, based on the user's supplied terms. The
copyright grant excludes redistribution, changes and new works based on the software.
Preserve **LICENSE**, **LICENSING.md**, the Pioneertown B.V. notice and Goran Mitevski's author
credit in licensor-authorized distributions and new starters. This change does not rewrite
older grants or change the Labtune upstream project's licence. It grants no rights beyond
the licensor's authority; general-purpose dependencies and other separately licensed material
retain their own notices and licences.

Historical serialized names can be read for compatibility; original saved bindings are
verified before presentation normalization. This is provenance, not a claim that the
underlying work was invented independently of Labtune.


Multiple-team orchestration is implemented in this repository's `teamknitt.teams` and native
engine. User-selected external style URLs are references only: no skills, prompts, templates,
configuration code or CLIs from those projects are copied, adapted, imported or executed.
Local style context is explicitly user-authored workspace input, not a claim of implementing
a referenced protocol or automatic verification of its authorship.
