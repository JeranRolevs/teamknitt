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

The **Labtune Academic Research License 2.0** and the legal texts **LICENSE** and **LICENSING.md**
are unchanged. The product name and broader task capabilities do not expand eligibility or
permit commercial use. Preserve both legal texts, the Pioneertown B.V. notice and Goran
Mitevski's author credit. General-purpose dependencies retain their own notices/licenses.

Historical serialized names can be read for compatibility; original saved bindings are
verified before presentation normalization. This is provenance, not a claim that the
underlying work was invented independently of Labtune.
