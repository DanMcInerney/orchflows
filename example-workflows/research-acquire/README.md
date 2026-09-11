# Research Acquire

Optional public-source acquisition with bounded requests, receipts and resumable discovery/selection/depth. It runs inside an existing worker; it creates no agents or reviews. Any research workflow can consume its evidence packets.

Install this complete library with `scripts/orchflows.py setup --example research-acquire` from an orchflows-light checkout. Use `resolve research-acquire --skill research-acquire` through the installed core CLI to locate its [entrypoint](skills/research-acquire/SKILL.md). It needs Python 3.9+ and the standard library; the orchflows home runtime satisfies that requirement. Native search in social-search does not depend on this package.

Reuse the caller's run/output context. For standalone use, load the available `orchflows-light:record-run` skill for one outer `research-acquire:research-acquire` run; missing history does not prevent acquisition. Scripts resolve from the loaded skill directory, and generated evidence belongs outside the package.

The backend and fixtures come from [the original recent-search library](https://github.com/DanMcInerney/orchflows/tree/945546721732aa564a086ee9543803b38017e1c3/example-workflows/recent-search), under the retained [MIT license](LICENSE). Executable scripts and tests are unchanged by extraction. Historical route measurements do not establish present access. Enforcement applies per plan; the caller allocates bounds across concurrent plans.

For offline validation, set `PYTHONPATH` to the skill's absolute `scripts/` directory and run `python -m unittest tests.test_skill_contract` from that skill directory. Run `scripts/acquire_fixture.py --output <scratch>` there to exercise parsing, selection, depth and resume. These checks do not test live access or research judgment.
