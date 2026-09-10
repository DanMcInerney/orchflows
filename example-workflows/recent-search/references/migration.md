# Recent search entry points

`recent-search` replaces the gallery workflow `super-research`. The package
carries the [private acquisition method](../skills/research-acquire/SKILL.md), including scripts, tests and references,
when installed or copied to a ring's workflows/recent-search/ directory. The method
is private; it resolves only under this public package's frame.

The former project `.orchflows/skills/research-acquire/` and its generated
`.agents` / `.claude` adapters are retired. Replace a caller's direct
`do --skill research-acquire` with a public `recent-search` invocation using
`output=evidence`, the same question, sources, policy, rigor, window, horizon,
caps and evidence store, and the caller's frame and output probe. The 3D game's
discovery helper makes this public call per question cluster. Package name
resolution follows [composition](../../../rules/composition.md).

Python clients retain the `super_research` module and manifest v2 APIs. Set
`PYTHONPATH` to the resolved public package's
skills/research-acquire/scripts/ directory containing the
[Python package entry](../skills/research-acquire/scripts/super_research/__init__.py) and use the interpreter returned by
`orchflows env workflow recent-search`. Copy the whole directory so code and
references remain in its pin; a copied public manifest alone is incomplete.

Regenerate managed host adapters with the normal installer / `orchflows sync`
doors. A retired generated adapter may be pruned by its generator; unrelated
home skills or workflows with the old name remain user-owned and are outside
this migration. Historical research and sealed evidence retain their original
names and paths.
