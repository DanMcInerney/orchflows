# Home, runtime and run context

Read this once at the independent entrypoint. Composed skills and children reuse the caller's resolved context. Relative links resolve from their containing file. This library's root is the directory containing `plugin.json`; retain that whole package when copying or loading a native cached copy.

## Resolve the boundary

Bootstrap orchflows-light with Python 3.11+ before using either the repository example or a home copy: run its `scripts/orchflows.py setup --example social-search`, optionally with `--home <absolute-home>` and `--source <absolute-core-package>`. Setup creates the home runtime and installs the core; it does not register native plugins or overwrite an existing user library. Restoration after cloning a home without `.local/` requires an available core bundle or supplied source. Do not invent an installation URL.

Choose home from the caller's explicit path, then `ORCHFLOWS_HOME`, then `~/.orchflows`. The runtime interpreter is `<home>/.local/runtime/Scripts/python.exe` on Windows or `<home>/.local/runtime/bin/python` on POSIX. The installed CLI is `<home>/.local/packages/orchflows-light/scripts/orchflows.py`. Invoke that script using the explicit runtime interpreter, independent of the project working directory. Use the host shell's normal argument quoting (`&` before a quoted executable in PowerShell).

At the boundary, use the CLI's JSON results (`package_root`, `skill_path` or `resource_path`, and `runtime_python`) to locate each needed dependency; load only what this invocation uses:

```text
<python> <core-cli> resolve orchflows-light --skill delegate-work --home <home>
<python> <core-cli> resolve orchflows-light --resource standards/research.md --home <home>
<python> <core-cli> resolve orchflows-light --resource standards/writing.md --home <home>
<python> <core-cli> resolve orchflows-light --resource docs/native-hosts.md --home <home>
```

The orchestrator also resolves `delegate-review` only for a requested separate review. A caller outside the library can locate its entrypoint with `resolve social-search --skill social-search`; named-domain work can use `--skill search-site`. Resolve a loaded repository/native-cache library's internal links within that loaded package; do not mix its resources with another installed version. Core identities use `orchflows-light:skill-name`; this library uses `social-search:skill-name` regardless of disk or native cache location. If the runtime, CLI or a required dependency is missing, report that setup gap before starting acquisition. Core resources never resolve through `../../` into a source checkout.

## One outer run

An independent invocation starts one run before doing work. For social-search:

```text
<python> <core-cli> run start --workflow social-search:social-search --home <home>
```

Add `--project <alias>` only when the caller supplies an alias. A standalone component uses its own `social-search:<skill-name>` identity; when a source profile loads search-site, retain the originally invoked profile's identity. A nested invocation reuses the caller's run and does not start or finish another one. Create default output directories inside the returned run directory, such as `artifacts/sources/<site>/` and `artifacts/report/`; keep acquisition responses and resumable evidence together under their source directory. Use the caller's explicit output path when requested, retaining a report reference in the run summary. Keep all generated files outside the installed library.

Pass children and composed skills the concrete library root, home, runtime interpreter, core CLI, resolved core skill/resource paths, run directory and unique output directory, plus resolved scope and limits. State which caller owns finalization. These are ordinary assignment context, not another metadata schema. Helpers reuse these paths without repeating setup, resolution or logging. They may read supporting files shared by the caller but must keep their own writable results separate.

The run owner writes an actual compact Markdown summary with outcome, report/evidence locations, required gaps, checks performed and any existing host-log references worth retaining. Record measured usage only when available; do not invent tool counts or reconstruct native transcripts. Finalize once:

```text
<python> <core-cli> run finish <run-dir> --status complete --summary <absolute-summary-file> --home <home>
```

Choose `partial` or `blocked` when required work remains; a standalone `no_results` source result maps to a completed run only when its bounded assignment finished. Reuse existing receipts and packet digests instead of copying raw evidence into metadata. Raw responses and bulk artifacts are Gitignored by default, while the compact run record and summary remain trackable; a summary link to ignored or project-local evidence does not make that evidence portable. Report unavailable logging honestly rather than asserting a run was recorded.
