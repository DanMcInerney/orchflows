# Library context

Reuse supplied context, otherwise establish it at the outer entrypoint, including either leaf invoked alone. Resolve core primitives and `orchflows-light:docs/architecture.md`; its guidance-selection rule applies here. Composed workflows and workers inherit concrete paths, the question, constraints and output directories.

Use available native skills or caller-supplied package roots. With a configured home (`--home`, `ORCHFLOWS_HOME`, then `~/.orchflows`), any Python 3.11+ can run `.local/packages/orchflows-light/scripts/orchflows.py`. Setup provides `.local/runtime/Scripts/python.exe` on Windows or `.local/runtime/bin/python` elsewhere:

```text
<python> <cli> resolve <library> --skill <name> --home <home>
<python> <cli> resolve <library> --resource <relative-path> --home <home>
```

For collection, select `research.search-site.web` for web discovery and `research.search-site.feeds` for a supplied feed URL set. A named site uses `research.search-site.<site>` when supplied here, otherwise `research.search-site`; a Lemmy instance uses `research.search-site.lemmy`. Combine applicable names for closely related sources sharing an assignment. For the final assessment, select `research.search-site` and `writing`, including the shared source guidance's Review section. Include caller-supplied guidance names and package roots; pass the resolved files to the relevant primitive.

Resolve optional research-acquire readers once for the chosen assignments: `skills/research-acquire/scripts/acquire.py`, `references/acquisition.md` and `references/selection-routes.md` under that skill for supported public collection sources; `scripts/inspect_source.py` and `references/source-inspection.md` under the same skill for YouTube transcripts. The usage references own supported routes and invocation contracts. Pass concrete paths and a suitable Python to workers that can use them. Generic feeds require research-acquire 0.4.0 or later. Native public tools can cover assigned sources, including explicit requests outside the optional reader's roster, when the resulting evidence is inspectable. Record access gaps; a missing reader or home runtime alone is not a blocker. Required missing skills or guidance are blockers; without native delegation the workflow is blocked.

Outputs go to the caller's location or a task directory in the caller's workspace, with a separate evidence directory per assignment and a report directory.
