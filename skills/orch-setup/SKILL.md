---
name: orch-setup
description: Set up or restore a portable orchflows home with a local Python runtime and installed core package, and resolve user-owned workflow libraries from any project.
---

Choose the home from an explicit user path, then `ORCHFLOWS_HOME`, then `~/.orchflows`. Resolve the [bootstrap CLI](../../scripts/orchflows.py) from this loaded core package, not the current project. Use an existing home runtime if available; the first bootstrap requires Python 3.11 or newer. Invoke that interpreter and the absolute script path with:

```text
setup --home HOME
```

Replace `HOME` with the chosen path. The script defaults its source to the package containing it; add `--source SOURCE_PACKAGE` when restoring from a separately supplied core bundle. Add `--example social-search` only when the user wants that example. An installed core copy may lack examples; treat the returned gap as a request for a real supplied example package, not permission to invent or fetch one from an unknown URL.

Normal setup sets concurrency to 15 in both hosts' user configs: Codex's cap on open spawned-agent threads excluding the primary, and Claude Code's shared cap on parallel read-only tools and subagents. Honor a requested value with `--concurrency N`, or a request to preserve host settings with `--skip-host-config`. Host paths follow `CODEX_HOME`/`CLAUDE_CONFIG_DIR` or their native defaults, independently of `HOME`. Inspect `host_configs` for changed paths and backups; start fresh host sessions afterward. See [native-hosts](../../docs/native-hosts.md#concurrency-defaults) for exact settings, unsupported layouts, and precedence. Do not claim the running session's capacity changed.

Inspect the returned JSON paths and status. Setup owns the machine-local runtime and managed core copy under `.local/`; portable configuration, custom libraries and compact run history belong to the user. Repeated setup must preserve home files, custom library content, unrelated host settings, and malformed configuration for inspection. Do not reset an unrelated environment, install undeclared dependencies, modify a legacy backup, or commit or publish the home. Library-specific Python dependencies remain declared with that library and use ordinary dependency tooling when authorized.

After bootstrap, use the returned runtime interpreter and installed `.local/packages/orchflows-light/scripts/orchflows.py` for all operations. The interpreter is `.local/runtime/Scripts/python.exe` on Windows or `.local/runtime/bin/python` elsewhere. Run `doctor --home HOME` to inspect actual runtime, package and library gaps. A restored Git clone needs `.local/` rebuilt from an installed/native core package or supplied bundle; portable configuration alone does not provide the package bytes.

Resolve a library boundary once using the installed CLI:

```text
resolve orchflows-light --resource standards/writing.md --home HOME
resolve personal --skill my-workflow --home HOME
```

Use the returned `package_root`, resource or skill path and runtime interpreter; pass concrete paths to composed skills and workers. Core resources live in the installed core package, while custom packages live in `HOME/libraries/LIBRARY`. Resolve links inside each package from their containing file. Do not hard-code paths from a custom library back into a source checkout or native host cache.

Create newly authored workflows in `HOME/libraries/personal/skills/` unless the caller selects another library or explicit destination. Preserve an explicit repository example path. Set up a custom library's native manifest and its `skills/` together when needed, keeping its package identity stable and its resources inside the package.

Home setup and native skill discovery are separate operations. Check [native-hosts](../../docs/native-hosts.md) and the current host's actual registration/update support before claiming that a library is invokable. Source libraries remain authoritative; hosts may cache installed packages and require a refresh or new session. Report what was installed, which paths resolve, and any remaining discovery step.
