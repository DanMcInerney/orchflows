# Library context

Reuse supplied context, otherwise establish it at the outer entrypoint, including either leaf invoked alone. Resolve core primitives and `orchflows-light:docs/architecture.md`; its guidance-selection rule applies here. Composed workflows and workers inherit concrete paths, the question, constraints and output directories.

Use available native skills or caller-supplied package roots. With a configured home (`--home`, `ORCHFLOWS_HOME`, then `~/.orchflows`), any Python 3.11+ can run `.local/packages/orchflows-light/scripts/orchflows.py`. Setup provides `.local/runtime/Scripts/python.exe` on Windows or `.local/runtime/bin/python` elsewhere:

```text
<python> <cli> resolve <library> --skill <name> --home <home>
<python> <cli> resolve <library> --resource <relative-path> --home <home>
```

For collection, select `research.search-site.web` for web discovery and `research.search-site.feeds` for a supplied feed URL set. A named site uses `research.search-site.<site>` when supplied here, otherwise `research.search-site`; a Lemmy instance uses `research.search-site.lemmy`. These names describe the assignment's source scope, not a worker per URL. For the final assessment, select `research` and `writing`. Include caller-supplied guidance names and package roots; pass the resolved files to the relevant primitive.

Resolve optional research-acquire readers only for assignments that use them: `skills/research-acquire/scripts/inspect_source.py` and `references/source-inspection.md` under that skill for YouTube; `scripts/acquire.py`, `references/acquisition.md` and `references/selection-routes.md` under the same skill for web or feeds. Pass concrete paths and a suitable Python to each worker; their usage references own the invocation contract. Generic feeds require research-acquire 0.4.0 or later. Without a suitable reader, use native tools and record any resulting evidence gap; a missing home runtime alone is not a blocker. Required missing skills or guidance are blockers; without native delegation the workflow is blocked.

Outputs go to the caller's location or a task directory in the caller's workspace, with a separate evidence directory per assignment and a report directory.
