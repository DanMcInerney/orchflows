# Library context

Resolve dependencies once at the outer entrypoint; composed workflows and workers inherit the concrete paths, question, constraints, output directories and run owner. Resolve this library's relative links within the loaded package.

Use the available orchflows-light native skills or caller-supplied core paths. With a configured home, its CLI can locate dependencies:

```text
<runtime-python> <core-cli> resolve orchflows-light --skill <name> --home <home>
<runtime-python> <core-cli> resolve orchflows-light --resource standards/research.md --home <home>
```

Home is the caller's choice, then `ORCHFLOWS_HOME`, then `~/.orchflows`. Runtime and CLI are `.local/runtime/Scripts/python.exe` on Windows (`.local/runtime/bin/python` elsewhere) and `.local/packages/orchflows-light/scripts/orchflows.py` beneath home. Use returned absolute paths. Load delegate-work or delegate-review and Research or Writing as needed. Resolve optional libraries by their own package identity.

For sources with [scripted readers](source-readers.md), resolve available readers once and pass their paths and runtime to workers.

Compose orchflows-light:record-run once for history; it owns start, finish and unavailable-runtime behavior. Normal outputs belong in the home run's `artifacts/`, with separate source and report directories. Honor explicit output locations and keep generated files outside packages.

A missing runtime does not block native research when core skills are available; record the history gap and use the caller's output workspace. Missing native delegation or a required core skill is a workflow blocker. Pass context onward without repeating setup, resolution or logging.
