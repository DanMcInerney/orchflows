# Your portable orchflows home

`~/.orchflows` holds your authored libraries and local runtime. `ORCHFLOWS_HOME` changes the default; an explicit `--home` wins. A project's working directory does not change which home is used.

## Bootstrap and runtime

Run `scripts/orchflows.py setup --example social-search` using Python 3.11+ from a complete core package or checkout. Setup creates a fresh venv at `.local/runtime/`, copies the core into `.local/packages/orchflows-light/`, and seeds the example in `libraries/social-search/` when absent. It installs no third-party Python dependencies. Libraries declare any additional script dependencies themselves; conflicting dependencies can use separate ignored environments under `.local/envs/`.

Setup also applies 15 to Codex's spawned-thread cap and Claude Code's shared tool/subagent cap in their user config files. `--concurrency N` overrides the value; `--skip-host-config` leaves both hosts alone. Host directories come from `CODEX_HOME` and `CLAUDE_CONFIG_DIR`, otherwise `~/.codex` and `~/.claude`, independently of the orchflows `--home` path. The JSON result's `host_configs` records each path, setting, value, change status, and backup path. [Native host settings](native-hosts.md#concurrency-defaults) explains preservation, failure handling, and the different limits. Restart the hosts after setup; higher-priority settings may override these user defaults.

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

Setup is additive initialization, not a core upgrade command. Repeat setup reuses matching managed files and the runtime, preserves user libraries, home configuration and catalogs, and reapplies the selected host concurrency value unless opted out. Malformed configuration, an unrelated runtime or a differing installed core is reported instead of overwritten. Before replacing a managed core for an upgrade, preserve any local edits and supply the intended complete core version; no automatic upgrade/merge is implemented here.

## Libraries are native packages

Use `libraries/<library>/skills/<skill>/SKILL.md` for both helpers and orchestration. A library has a portable `plugin.json` identity, native compatibility manifests, a README and any dependencies or trial material it needs. The resolver also accepts native-only manifests. Keep native names unique across installed libraries.

Relative links resolve within the loaded package. Resolve an external dependency by package name at the composition boundary and pass its concrete paths onward. For example, `social-search` resolves installed `orchflows-light` Research/Writing standards and delegation skills once, while source profiles link directly to sibling `search-site` and `prepare-evidence` skills.

`setup --example NAME` installs any matching named package from the source's `example-workflows/`. For example, `research-acquire` is an optional acquisition library independent of `social-search`. New home catalogs include the core and valid installed libraries. Existing catalogs remain user-owned: setup reports missing registrations without rewriting them. Register a new library in the relevant native catalog, install it with the host, and refresh cached plugins after source edits. Directly asking an agent to read an absolute `SKILL.md` path also works without named host discovery.

Use the [native host guide](native-hosts.md) for registration and reload commands. Core development may still load the source checkout directly; user custom workflows belong in their home library unless a project-local destination was requested.

## Outputs and history

Use the caller's output location or a task-specific directory in its workspace.
Keep generated evidence and reports outside installed packages, and pass concrete
output paths to workers. Save a summary when it helps the user; workflows do not
need run registration or finalization.

The native hosts retain their own history. `history find`, `history inspect` and
`history read` retrieve that evidence for troubleshooting and `orch-self-improve`;
see [native history](native-history.md). Existing home logs and reports from earlier
versions remain ordinary files and are preserved by setup. The manual `run start`
and `run finish` commands have been removed.

## Git and another computer

Generated ignore rules keep `.local/`, Python caches and an optional home
`artifacts/` directory out of Git. Portable configuration, libraries and catalogs
remain eligible for tracking. Review reports before committing them. Setup never
commits or pushes and preserves existing ignore rules, Git attributes and saved
logs.

After cloning your home to another computer:

1. Obtain the intended orchflows-light core package or checkout, matching the identity recorded in `config.toml`.
2. Run that package's setup with `--home` pointing at the clone. The default source is the package containing the CLI; `--source` can select another complete bundle.
3. Recreate library-specific Python dependencies from its declared requirements.
4. Register the cloned home's native marketplace and install the libraries you use. Start a new host session.

No source download or lockfile-driven restore is promised. Portable config records core provenance; machine paths are kept in ignored `.local/config.toml`. An absent venv is recreated in its final location, never copied across computers. A supplied source may differ from the recorded identity; inspect setup/doctor's reported mismatch before using it.
