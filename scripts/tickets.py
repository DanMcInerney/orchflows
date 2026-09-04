#!/usr/bin/env python3
"""Current sealed ticket commands over the user-scope state sink.

The author-facing semantic payload is Goal, Context, and optional Suggested
files. Every command emits one JSON document; a payload carrying ``error``
exits 1 and every other payload exits 0. ``--help`` owns the live command
list.

The run identity at ``<sink>/runs/<run>/run.json`` records exactly `run`,
`sink_convention`, `opened_at`, `orchflows`, `orchflows.receipt_version`,
`orchflows.source_commit`, `terminal_at`, `terminal_ticket_id`,
`terminal_status`, `elapsed_ms`, `project`, `project.root`,
`project.origin`, `project.name`, `workspaces`, `workspaces[].path`, and
`workspaces[].first_seen`.

Every name re-exported below is one something outside the family reads
here. A re-export nothing names is a second owner for one fact, so it is
deleted instead.
"""

from __future__ import annotations

import sys as _bootstrap_sys
from pathlib import Path as _BootstrapPath

_SIBLING_DIR = str(_BootstrapPath(__file__).resolve().parent)
if _SIBLING_DIR not in _bootstrap_sys.path:
    _bootstrap_sys.path.append(_SIBLING_DIR)

if __package__:
    from . import tickets_adapters as _tickets_adapters_module
    from . import tickets_format as _tickets_format_module
    from . import tickets_store as _tickets_store_module
    from . import tickets_issue as _tickets_issue_module
    from . import tickets_lifecycle as _tickets_lifecycle_module
    from . import tickets_result as _tickets_result_module
    from . import tickets_commands as _tickets_commands_module
    from . import tickets_lint as _tickets_lint_module
    from . import tickets_dispatch as _tickets_dispatch_module
    from . import tickets_dispatch_facade as _tickets_dispatch_facade_module
    from . import tickets_admission as _tickets_admission_module
    from . import tickets_attempts as _tickets_attempts_module
    from . import tickets_land as _tickets_land_module
    from . import tickets_registry as _tickets_registry_module
else:
    # By name, as `tickets_generations` is reached: the family's
    # module-level import census is pinned.
    import tickets_adapters as _tickets_adapters_module
    import tickets_format as _tickets_format_module
    import tickets_store as _tickets_store_module
    import tickets_issue as _tickets_issue_module
    import tickets_lifecycle as _tickets_lifecycle_module
    import tickets_result as _tickets_result_module
    import tickets_commands as _tickets_commands_module
    import tickets_lint as _tickets_lint_module
    import tickets_dispatch as _tickets_dispatch_module
    import tickets_dispatch_facade as _tickets_dispatch_facade_module
    import tickets_admission as _tickets_admission_module
    import tickets_attempts as _tickets_attempts_module
    import tickets_land as _tickets_land_module
    _tickets_registry_module = __import__('tickets_registry')

REQUIRED_ISOLATION = _tickets_format_module.REQUIRED_ISOLATION
TERMINAL_STATES = _tickets_format_module.TERMINAL_STATES
_parse_bound_minutes = _tickets_format_module._parse_bound_minutes
_parse_frontmatter = _tickets_format_module._parse_frontmatter
_sections = _tickets_format_module._sections
_set_frontmatter_field = _tickets_format_module._set_frontmatter_field
ticket_defects = _tickets_format_module.ticket_defects
CALLABLE_EXECUTORS = _tickets_registry_module.CALLABLE_EXECUTORS
ADAPTER_REGISTRY = _tickets_adapters_module.ADAPTER_REGISTRY
Adapter = _tickets_adapters_module.Adapter
AdapterError = _tickets_adapters_module.AdapterError
adapter_id = _tickets_adapters_module.adapter_id
adapter_spec = _tickets_adapters_module.adapter_spec
derived_isolation = _tickets_adapters_module.derived_isolation
binding_findings = _tickets_admission_module.binding_findings
grade_admission = _tickets_admission_module.grade_admission
_GENERATION_EXPORTS = frozenset({"assignment_digest", "assignment_payload"})


def __getattr__(name):
    """Load generation algebra only when a caller asks for it."""
    if name not in _GENERATION_EXPORTS:
        raise AttributeError(name)
    qualified = f"{__package__}.tickets_generations" if __package__ else "tickets_generations"
    module = __import__(qualified, fromlist=[name])
    value = getattr(module, name)
    globals()[name] = value
    return value
DEFAULT_RUN_STATE_TREE = _tickets_store_module.DEFAULT_RUN_STATE_TREE
RUN_IDENTITY_NAME = _tickets_store_module.RUN_IDENTITY_NAME
RUN_NOTES_NAME = _tickets_store_module.RUN_NOTES_NAME
RUN_STATE_TREES = _tickets_store_module.RUN_STATE_TREES
SINK_CONVENTION = _tickets_store_module.SINK_CONVENTION
UTC_STAMP = _tickets_store_module.UTC_STAMP
_cwd = _tickets_store_module._cwd
_find_repo_root = _tickets_store_module._find_repo_root
_identity_document = _tickets_store_module._identity_document
def _installed_orchflows_metadata() -> dict:
    """Return the installed library identity through its store owner."""
    return _tickets_store_module._installed_orchflows_metadata()
_load_ticket = _tickets_store_module._load_ticket
_main_checkout_root = _tickets_store_module._main_checkout_root
_origin_url = _tickets_store_module._origin_url
_project_key = _tickets_store_module._project_key
_read_identity = _tickets_store_module._read_identity
_replace_atomically = _tickets_store_module._replace_atomically
_runs_root = _tickets_store_module._runs_root
_same_project = _tickets_store_module._same_project
def _terminal_identity_update(run: str, ticket_id: str, status: str, now):
    """Return the terminal identity update through its store owner."""
    return _tickets_store_module._terminal_identity_update(run, ticket_id, status, now)
_tickets_root = _tickets_store_module._tickets_root
_write_identity = _tickets_store_module._write_identity
_write_text_atomically = _tickets_store_module._write_text_atomically
_writer_identity = _tickets_store_module._writer_identity
state_root = _tickets_store_module.state_root
_cmd_ready = _tickets_lifecycle_module._cmd_ready
COVERAGE_RECORD_NAME = _tickets_result_module.COVERAGE_RECORD_NAME
PROPOSALS_DIR = _tickets_result_module.PROPOSALS_DIR
TERMINAL_HEADING = _tickets_result_module.TERMINAL_HEADING
_append_one_line = _tickets_result_module._append_one_line
_cmd_dispatch_open = _tickets_attempts_module._cmd_dispatch_open
_cmd_dispatch_retire = _tickets_attempts_module._cmd_dispatch_retire
SUBCOMMAND_SUMMARY = _tickets_commands_module.SUBCOMMAND_SUMMARY
SUBCOMMAND_USAGE = _tickets_commands_module.SUBCOMMAND_USAGE
_cmd_help = _tickets_dispatch_module._cmd_help
_dispatch = _tickets_dispatch_module._dispatch
main = _tickets_dispatch_module.main
console = _tickets_dispatch_module.console

def _sync_seams():
    """Re-point at their owners the seams a check patches on this facade."""
    _tickets_store_module._cwd = _cwd
    _tickets_store_module._write_identity = _write_identity
    _tickets_issue_module._write_identity = _write_identity
    _tickets_lifecycle_module._write_identity = _write_identity
    _tickets_result_module._write_identity = _write_identity
    _tickets_dispatch_module._write_identity = _write_identity
    _tickets_store_module._write_text_atomically = _write_text_atomically
    _tickets_lifecycle_module._write_text_atomically = _write_text_atomically
    _tickets_result_module._write_text_atomically = _write_text_atomically
    _tickets_attempts_module._write_text_atomically = _write_text_atomically
    _tickets_lint_module._write_text_atomically = _write_text_atomically
    _tickets_result_module._append_one_line = _append_one_line
    _tickets_dispatch_module._cmd_dispatch_open = _cmd_dispatch_open
    _tickets_dispatch_facade_module._cmd_dispatch_open = _cmd_dispatch_open
    _tickets_dispatch_facade_module._cmd_dispatch_retire = _cmd_dispatch_retire
    _tickets_dispatch_module._cmd_ready = _cmd_ready
    _tickets_dispatch_facade_module._cmd_ready = _cmd_ready

# Handed down, never fetched back up: the dispatcher calls this once per
# invocation and no helper imports this facade to reach it.
_tickets_dispatch_module._sync_seams = _sync_seams

if __name__ == "__main__":
    raise SystemExit(console.run(main))
