# Your portable orchflows home

`~/.orchflows` holds your authored libraries and workflow history. `ORCHFLOWS_HOME` changes the default; an explicit `--home` wins. A project's working directory does not change which home is used.

## Bootstrap and runtime

Run `scripts/orchflows.py setup --example social-search` using Python 3.11+ from a complete core package or checkout. Setup creates a fresh venv at `.local/runtime/`, copies the core into `.local/packages/orchflows-light/`, and seeds the example in `libraries/social-search/` when absent. It installs no third-party Python dependencies. Libraries declare any additional script dependencies themselves; conflicting dependencies can use separate ignored environments under `.local/envs/`.

Use the returned `runtime_python` path and the installed CLI afterward. Activation is optional. For example, from any PowerShell working directory:

```powershell
$orchflowsRoot = Join-Path $env:USERPROFILE '.orchflows'
$orchflowsPython = Join-Path $orchflowsRoot '.local/runtime/Scripts/python.exe'
$orchflowsCli = Join-Path $orchflowsRoot '.local/packages/orchflows-light/scripts/orchflows.py'
& $orchflowsPython $orchflowsCli doctor --home $orchflowsRoot
& $orchflowsPython $orchflowsCli resolve social-search --skill search-reddit --home $orchflowsRoot
& $orchflowsPython $orchflowsCli resolve orchflows-light --resource standards/research.md --home $orchflowsRoot
```

On macOS/Linux the interpreter is `.local/runtime/bin/python`. Use your selected home or setup's returned paths when overridden. Resolution returns a package root and requested skill/resource path. It rejects escaping paths and duplicate package identities. It does not install dependencies or execute a workflow.

Setup is additive initialization, not a core upgrade command. Repeat setup reuses matching managed files and the runtime, and preserves user libraries, configuration and catalogs. Malformed configuration, an unrelated runtime or a differing installed core is reported instead of overwritten. Before replacing a managed core for an upgrade, preserve any local edits and supply the intended complete core version; no automatic upgrade/merge is implemented here.

## Libraries are native packages

Use `libraries/<library>/skills/<skill>/SKILL.md` for both helpers and orchestration. A library has a portable `plugin.json` identity, native compatibility manifests, a README and any dependencies or trial material it needs. The resolver also accepts native-only manifests. Keep native names unique across installed libraries.

Relative links resolve within the loaded package. Resolve an external dependency by package name at the composition boundary and pass its concrete paths onward. For example, `social-search` resolves installed `orchflows-light` Research/Writing standards and delegation skills once, while source profiles link directly to sibling `search-site` and `prepare-evidence` skills.

`setup --example NAME` installs any matching named package from the source's `example-workflows/`. For example, `research-acquire` is an optional acquisition library independent of `social-search`. New home catalogs include the core and valid installed libraries. Existing catalogs remain user-owned: setup reports missing registrations without rewriting them. Register a new library in the relevant native catalog, install it with the host, and refresh cached plugins after source edits. Directly asking an agent to read an absolute `SKILL.md` path also works without named host discovery.

Use the [native host guide](native-hosts.md) for registration and reload commands. Core development may still load the source checkout directly; user custom workflows belong in their home library unless a project-local destination was requested.

## One run per outer workflow

`record-run` starts a run at the outer workflow boundary. Nested workflows and source workers reuse its context. Run directories are unique so concurrent sessions do not share a writable global log.

```sh
python /absolute/home/.local/packages/orchflows-light/scripts/orchflows.py run start --workflow social-search:social-search --project demo
python /absolute/home/.local/packages/orchflows-light/scripts/orchflows.py run finish /absolute/home/logs/YYYY-MM/RUN --status complete --summary /absolute/path/to/actual-summary.md
```

Use the home runtime interpreter in place of `python` and pass `--home` for a non-default home. Save an actual outcome summary, including limitations, before finalization. `partial` and `blocked` are available when work cannot fully complete. A started run remains `running` if the host stops before finalization; that is unfinished metadata, not a background process. Final records are immutable except an identical repeated finish.

Logs record workflow identity, available provenance, timestamps, status and the supplied summary. They do not automatically capture full native conversations, token usage or tool calls. Preserve real host receipts when available; never invent missing telemetry. Workflows must call the logging skill to participate. A requested project artifact can remain in that project while the home summary records its location.

## Git and another computer

Generated ignore rules keep `.local/`, Python caches and run bulk output out of Git. Portable configuration, libraries, catalogs, `run.json` and `summary.md` remain eligible for tracking. Review which summaries you want to share before committing. Setup never commits or pushes.

Commit the seeded home `.gitattributes` too. Its `/logs/**/run.json -text` and `/logs/**/summary.md -text` rules preserve exact run bytes on Git add and checkout, including LF or CRLF summary line endings. This keeps the summary's recorded SHA-256 valid across computers with different `core.autocrlf` settings. Setup preserves an existing attributes file; setup and doctor use Git to report missing byte-preservation rules for representative run paths. Review any reported gaps before committing logs. Adding attributes cannot recover bytes already changed in an earlier commit or checkout.

After cloning your home to another computer:

1. Obtain the intended orchflows-light core package or checkout, matching the identity recorded in `config.toml`.
2. Run that package's setup with `--home` pointing at the clone. The default source is the package containing the CLI; `--source` can select another complete bundle.
3. Recreate library-specific Python dependencies from its declared requirements.
4. Register the cloned home's native marketplace and install the libraries you use. Start a new host session.

No source download or lockfile-driven restore is promised. Portable config records core provenance; machine paths are kept in ignored `.local/config.toml`. An absent venv is recreated in its final location, never copied across computers. A supplied source may differ from the recorded identity; inspect setup/doctor's reported mismatch before using it.
