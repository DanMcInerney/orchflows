# Library context

Resolve dependencies once at the outer entrypoint; composed workflows and workers inherit the concrete paths, question, constraints and output directories.

Use the installed orchflows-light native skills. With a configured home (`--home`, `ORCHFLOWS_HOME`, then `~/.orchflows`), its runtime `.local/runtime/Scripts/python.exe` on Windows or `.local/runtime/bin/python` elsewhere runs `.local/packages/orchflows-light/scripts/orchflows.py`:

```text
resolve orchflows-light --resource guidance/research.md --home <home>
resolve research-acquire --resource skills/research-acquire/scripts/inspect_source.py --home <home>
resolve research-acquire --resource skills/research-acquire/references/source-inspection.md --home <home>
```

The guidance for `research.search-site.<site>` is core `guidance/research.md`, then this library's `guidance/research.search-site.md` and `guidance/research.search-site.<site>.md`. The optional reader (second command; usage in the third) fetches a known YouTube transcript inside the worker; pass its path and the runtime to the worker. Without the home runtime or readers, native tools suffice and the gap is recorded; without native delegation the workflow is blocked.

Outputs go to the caller's location or a task directory in the caller's workspace, with separate source and report directories.
