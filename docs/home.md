# Home

```text
~/.orchflows/
├── config.toml                      core identity            tracked
├── README.md  .gitignore            seeded once              tracked
├── libraries/<library>/             user packages            tracked
├── .agents/plugins/marketplace.json Codex catalog            tracked
├── .claude-plugin/marketplace.json  Claude catalog           tracked
├── artifacts/                       optional scratch         ignored
└── .local/                          machine-specific         ignored
    ├── config.toml                  source, core, runtime paths
    ├── runtime/                     Python 3.11+ venv, no packages
    ├── packages/orchflows-light/    managed core; setup replaces it
    └── backups/core-<id>/           previous core and config after an update
```

Selection: `--home PATH`, then `ORCHFLOWS_HOME`, then `~/.orchflows`; the current directory never selects it. Interpreter: `.local/runtime/Scripts/python.exe` on Windows, `.local/runtime/bin/python` elsewhere. CLI: `.local/packages/orchflows-light/scripts/orchflows.py`, Python 3.11+ with no packages; `--help` lists flags. One JSON line on stdout; command errors are JSON on stderr with exit 2; `setup` and `doctor` exit 1 when `issues` is non-empty.

## setup

`python <checkout>/scripts/orchflows.py setup [--example NAME] [--source PKG] [--concurrency N | --skip-host-config]`

- Creates the tree above, the venv, the managed core, both `orchflows-home` catalogs, and `git init` when Git exists. Never commits.
- `--example NAME` copies `<source>/example-workflows/NAME` to `libraries/NAME/` once; an existing library is preserved. An installed core has no examples; supply a checkout.
- Rerun from the desired core to update. Identical content (name, version, SHA): `core.status` is `reused`. Different: previous core and `config.toml` go to `.local/backups/core-<id>/`, the new core is staged then swapped, `config.toml` identity is updated; failure restores the old core. A locally edited managed core or a config identity mismatch is `preserved` and reported; reconcile, then rerun.
- Catalogs gain missing entries; existing entries, order and custom sources stay. Conflicts are reported, not rewritten.
- Writes 15 to both hosts' user concurrency settings ([hosts.md](hosts.md)). Both files are validated before the home is touched: a malformed file, duplicate JSON keys, an inline `agents` table or a linked file aborts setup with exit 2 and no home; fix it or pass `--skip-host-config`. Unrelated TOML text survives byte-for-byte; Claude JSON is reformatted with two-space indent, values kept. A changed file gets a sibling `<file>.orchflows-<id>.bak`; a write failure is `host_config_status: partial`. New sessions read the value; project or managed settings may override it.
- A leftover `.local/packages/.setup.lock` or `<file>.orchflows.lock` means an installer may be running; delete only after checking.

Result: `status`, `home`, `files`, `runtime_python`, `core` (`status`, `package_root`, `name`, `version`, `content_sha256`; `backup_path` when `installed` or `updated`), `runtime`, `example`, `git`, `host_configs`, `host_config_status`, `issues`.

## doctor

Read-only: config files, core identity against `config.toml`, runtime, each library's manifest and `skills/`, catalog registrations, ignore rules.

## resolve

`resolve <library> [--skill NAME | --resource RELATIVE/PATH]`

Returns `package_root`, `version`, `skill_path` or `resource_path`, and an unverified `runtime_python`. `orchflows-light` is the managed core, holding `standards/*.md` and `docs/*.md`; any other name is `libraries/<name>`. Escaping or absolute resources and duplicate names are rejected. Any Python 3.11+ can run it; it launches nothing. No home or runtime: continue with native skills if present and report the gap; no native delegation is a blocker.

## Libraries

`libraries/<name>/` with a manifest (`plugin.json`, `.claude-plugin/plugin.json` or `.codex-plugin/plugin.json`) carrying `name` and `version`, and `skills/<skill>/SKILL.md`. Names are unique across the home and never `orchflows-light`. Edit here, never in `.local/packages/`. Register with the host after setup: [hosts.md](hosts.md).

## Another computer

`.local/`, `artifacts/` and caches are ignored; the rest is tracked. After cloning: run the intended core's `setup --home <clone>` (or `--source <bundle>`), reinstall library dependencies, register and install ([hosts.md](hosts.md)). Setup downloads nothing.
