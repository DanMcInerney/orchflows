# Library context

Reuse supplied context, otherwise establish it at the outer entrypoint, including either leaf invoked alone. Resolve core primitives and `orchflows-light:docs/architecture.md`; its guidance-selection rule applies here. Composed workflows and workers inherit concrete paths, the question, constraints and output directories.

Use available native skills or caller-supplied package roots. With a configured home (`--home`, `ORCHFLOWS_HOME`, then `~/.orchflows`), any Python 3.11+ can run `.local/packages/orchflows-light/scripts/orchflows.py`. Setup provides `.local/runtime/Scripts/python.exe` on Windows or `.local/runtime/bin/python` elsewhere:

```text
<python> <cli> resolve <library> --skill <name> --home <home>
<python> <cli> resolve <library> --resource <relative-path> --home <home>
```

For collection, select `research.search-site.<site>` when this library supplies that specialization, otherwise `research.search-site`. For the final assessment, select `research` and `writing`. Include caller-supplied guidance names and package roots; pass the resolved files to the relevant primitive.

For YouTube, optionally resolve `research-acquire:skills/research-acquire/scripts/inspect_source.py` and its `references/source-inspection.md` sibling under the skill directory. Pass that reader, its usage and a suitable Python to the worker. Without the reader, use native tools and record any resulting evidence gap; a missing home runtime alone is not a blocker. Required missing skills or guidance are blockers; without native delegation the workflow is blocked.

Outputs go to the caller's location or a task directory in the caller's workspace, with separate source and report directories.
