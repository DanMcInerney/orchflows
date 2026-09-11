# Provenance and checks

Rebuilt from [DanMcInerney/orchflows recent-search](https://github.com/DanMcInerney/orchflows/tree/945546721732aa564a086ee9543803b38017e1c3/example-workflows/recent-search), revision `945546721732aa564a086ee9543803b38017e1c3`. The accompanying [MIT license](../LICENSE) preserves the upstream copyright and permission notice.

This is an intentional orchflows-light adaptation, not an exact behavioral port. Social-search selects independently reusable site workflows, allocates a shared budget and runs fresh native source workers concurrently within actual capacity and origin limits. One fresh rank-research judge checks their supporting evidence, deduplicates and reranks it globally, then writes a concise ranked cited report with synthesis. At most one targeted evidence follow-up continues the original workers and then the same judge. Its final prose has no additional independent review unless requested. Evidence-only and offline HTML remain available; required source gaps prevent full completion even when a qualified partial answer is useful.

The package-local acquisition helpers, `super_research` adapters and offline regression fixtures are retained unchanged as an optional domain backend for supported public-platform reads, deterministic caps, receipts and resume. Native tools do not gain those guarantees. The backend's historical route measurements describe upstream observations, not present host access or new live verification. Top-level historical admission dossiers were omitted. Native delegation replaces tickets, frames, managed environments and workspace adapters; ordinary directory creation replaces `prepare_document.py`. The HTML criteria adapt the upstream standard for either native evidence or packets. Keep this package together so script-relative resolution and resumable package identity work.

The portable package places all callable skills under `skills/`, with prepare-evidence owning the shared handoff contract and rank-research owning the HTML criteria. The source profiles and acquisition skill retain their own capabilities. Core imports and the explicit runtime interpreter come from [home/runtime resolution](home-runtime.md); no executable backend code, adapters, tests or captured fixtures changed during this packaging.

For a focused packaging check, use an external virtual environment and scratch directory. Resolve `<method>` to `skills/research-acquire/` inside this package, set `PYTHONPATH` to its absolute `scripts/` path, and run from that method directory:

```text
<interpreter> -m unittest tests.test_skill_contract
<interpreter> <method>/scripts/acquire_fixture.py --output <scratch>/admission
```

The two contract tests exercise the acquisition entrypoint's required references and validate its documented plan, including rejection of a wrong cap. The fixture exercises real adapter parsers with offline responses, discovery/selection/depth linkage, and a completed resume with zero additional attempts and identical packet bytes. Compare preserved script/test bytes against the input revision and validate all eleven skill frontmatters, native manifests and package-local links as separate packaging checks.

The broader retained suite covers backend behavior and explicitly verifies its Python 3.9 compatibility floor; if backend changes warrant that suite, use a Python 3.9 environment and `-m unittest discover -s tests -t .`. Offline checks do not validate site selection, native-tool accounting, worker overlap, judge independence, ranking/report quality or current public-platform access. Native workflow behavior needs a separate [bounded trial](../trials/request.md) with actual worker intervals, returned evidence and judge output against its [acceptance criteria](../trials/expected-behavior.md); backend test totals are not evidence that the orchestration or every output mode has passed.

The earlier orchflows-light adaptation removed obsolete generated-host-mirror assertions because it loads native skills by actual paths and has no generated `.claude/skills/super-research` stub. This portable packaging preserves that existing test baseline. Acquisition, transport, policy, window, lineage, count, cap and resume regression coverage remains. Local Git attributes retain captured HTML response whitespace; the original fixture bytes are not reformatted to satisfy whitespace checks.
