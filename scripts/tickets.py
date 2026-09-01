#!/usr/bin/env python3
"""Current sealed ticket commands over the user-scope state sink.

The author-facing semantic payload is Goal, Context, and optional Suggested
files. Every command emits one JSON document; a payload carrying ``error``
exits 1 and every other payload exits 0. ``--help`` owns the live command list.

The run identity at ``<sink>/runs/<run>/run.json`` records exactly `run`,
`sink_convention`, `opened_at`, `orchflows`, `orchflows.receipt_version`,
`orchflows.source_commit`, `terminal_at`, `terminal_ticket_id`,
`terminal_status`, `elapsed_ms`, `project`, `project.root`, `project.origin`,
`project.name`, `workspaces`, `workspaces[].path`, and
`workspaces[].first_seen`.
"""

from __future__ import annotations

import sys as _bootstrap_sys
from pathlib import Path as _BootstrapPath

_SIBLING_DIR = str(_BootstrapPath(__file__).resolve().parent)
if _SIBLING_DIR not in _bootstrap_sys.path:
    _bootstrap_sys.path.append(_SIBLING_DIR)

if __package__:
    from . import tickets_adapters as _tickets_adapters_module
    from . import tickets_bound as _tickets_bound_module
    from . import tickets_format as _tickets_format_module
    from . import tickets_store as _tickets_store_module
    from . import tickets_store_writes as _tickets_store_writes_module
    from . import tickets_issue as _tickets_issue_module
    from . import tickets_lifecycle as _tickets_lifecycle_module
    from . import tickets_assignment as _tickets_assignment_module
    from . import tickets_result as _tickets_result_module
    from . import tickets_worklog as _tickets_worklog_module
    from . import tickets_commands as _tickets_commands_module
    from . import tickets_lint as _tickets_lint_module
    from . import tickets_dispatch as _tickets_dispatch_module
    from . import tickets_dispatch_facade as _tickets_dispatch_facade_module
    from . import tickets_admission as _tickets_admission_module
    from . import tickets_attempts as _tickets_attempts_module
    from . import tickets_join as _tickets_join_module
    from . import tickets_outcome as _tickets_outcome_module
    from . import tickets_land as _tickets_land_module
    from . import tickets_registry as _tickets_registry_module
    from . import tickets_grade as _tickets_grade_module
else:
    # By name, as `tickets_generations` is reached: the family's
    # module-level import census is pinned, and this module joined after it.
    import tickets_adapters as _tickets_adapters_module
    _tickets_bound_module = __import__('tickets_bound')
    import tickets_format as _tickets_format_module
    import tickets_store as _tickets_store_module
    import tickets_store_writes as _tickets_store_writes_module
    import tickets_issue as _tickets_issue_module
    import tickets_lifecycle as _tickets_lifecycle_module
    import tickets_assignment as _tickets_assignment_module
    import tickets_result as _tickets_result_module
    import tickets_worklog as _tickets_worklog_module
    import tickets_commands as _tickets_commands_module
    import tickets_lint as _tickets_lint_module
    import tickets_dispatch as _tickets_dispatch_module
    import tickets_dispatch_facade as _tickets_dispatch_facade_module
    import tickets_admission as _tickets_admission_module
    import tickets_attempts as _tickets_attempts_module
    import tickets_join as _tickets_join_module
    import tickets_outcome as _tickets_outcome_module
    import tickets_land as _tickets_land_module
    _tickets_registry_module = __import__('tickets_registry')
    _tickets_grade_module = __import__('tickets_grade')

BOUND_KINDS = _tickets_bound_module.BOUND_KINDS
OTHER_BOUND_KIND = _tickets_bound_module.OTHER_BOUND_KIND
TOOL_CALL_MINUTES = _tickets_bound_module.TOOL_CALL_MINUTES
parse_bound = _tickets_bound_module.parse_bound
_cmd_bound_check = _tickets_bound_module._cmd_bound_check
BOUND_CHECK_USAGE = _tickets_commands_module.BOUND_CHECK_USAGE
CUT_SECTIONS = _tickets_format_module.CUT_SECTIONS
CUT_SECTIONS_BY_KEY = _tickets_format_module.CUT_SECTIONS_BY_KEY
DEFAULT_BOUND_MINUTES = _tickets_format_module.DEFAULT_BOUND_MINUTES
DURATION_RE = _tickets_format_module.DURATION_RE
EXECUTOR_SECTIONS = _tickets_format_module.EXECUTOR_SECTIONS
EXECUTOR_SECTIONS_BY_KEY = _tickets_format_module.EXECUTOR_SECTIONS_BY_KEY
OPTIONAL_SECTIONS = _tickets_format_module.OPTIONAL_SECTIONS
PACKS_DIR = _tickets_worklog_module.PACKS_DIR
PACK_NAME_PREFIX = _tickets_format_module.PACK_NAME_PREFIX
PACK_NAME_SUFFIX = _tickets_format_module.PACK_NAME_SUFFIX
REQUIRED_ISOLATION = _tickets_format_module.REQUIRED_ISOLATION
REQUIRED_LIFECYCLE_KEYS = _tickets_format_module.REQUIRED_LIFECYCLE_KEYS
REQUIRED_SECTIONS = _tickets_format_module.REQUIRED_SECTIONS
REQUIRED_TICKET_KEYS = _tickets_format_module.REQUIRED_TICKET_KEYS
RESULT_TOKEN_SPLIT_RE = _tickets_format_module.RESULT_TOKEN_SPLIT_RE
RESULT_TOKEN_STRIP = _tickets_format_module.RESULT_TOKEN_STRIP
CHECKED_BY_KEY = _tickets_format_module.CHECKED_BY_KEY
CALLABLE_EXECUTORS = _tickets_registry_module.CALLABLE_EXECUTORS
EXECUTOR_REGISTRY = _tickets_registry_module.EXECUTOR_REGISTRY
GATE_ID_MARKER = _tickets_format_module.GATE_ID_MARKER
SCRIPT_EXECUTOR_PREFIX = _tickets_format_module.SCRIPT_EXECUTOR_PREFIX
SECTION_ORDER = _tickets_format_module.SECTION_ORDER
SECTION_RANK = _tickets_format_module.SECTION_RANK
TERMINAL_STATES = _tickets_format_module.TERMINAL_STATES
TicketFormatError = _tickets_format_module.TicketFormatError
VALID_STATUSES = _tickets_format_module.VALID_STATUSES
_body_block = _tickets_format_module._body_block
_executor_of = _tickets_format_module._executor_of
_extract_all = _tickets_format_module._extract_all
_extract_flag = _tickets_format_module._extract_flag
_fence_run = _tickets_format_module._fence_run
_frontmatter_end = _tickets_format_module._frontmatter_end
_frontmatter_line = _tickets_format_module._frontmatter_line
_heading_lines = _tickets_format_module._heading_lines
_parse_bound_minutes = _tickets_format_module._parse_bound_minutes
_parse_frontmatter = _tickets_format_module._parse_frontmatter
_parse_iso = _tickets_format_module._parse_iso
_read_utf8 = _tickets_format_module._read_utf8
_scan_sections = _tickets_format_module._scan_sections
_section_body = _tickets_format_module._section_body
_sections = _tickets_format_module._sections
_set_frontmatter_field = _tickets_format_module._set_frontmatter_field
_split_commas = _tickets_format_module._split_commas
_unquote = _tickets_format_module._unquote
dequote = _tickets_format_module.dequote
_write_section = _tickets_format_module._write_section
ticket_defects = _tickets_format_module.ticket_defects
ADMISSION_PENDING = _tickets_admission_module.ADMISSION_PENDING
ADAPTER_REGISTRY = _tickets_adapters_module.ADAPTER_REGISTRY
Adapter = _tickets_adapters_module.Adapter
AdapterError = _tickets_adapters_module.AdapterError
adapter_id = _tickets_adapters_module.adapter_id
adapter_spec = _tickets_adapters_module.adapter_spec
derived_isolation = _tickets_adapters_module.derived_isolation
binding_findings = _tickets_admission_module.binding_findings
grade_admission = _tickets_admission_module.grade_admission
is_receipt = _tickets_admission_module.is_receipt
_GENERATION_EXPORTS = frozenset({
    "assignment_digest", "assignment_payload", "correction_decision", "draft_snapshot",
    "generation_identity", "generation_ordinal", "seal_assignments",
    "seal_findings", "validate_draft",
})


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
NO_SINK_ERROR = _tickets_store_module.NO_SINK_ERROR
REPLACE_BUDGET_SECONDS = _tickets_store_module.REPLACE_BUDGET_SECONDS
REPLACE_RETRY_SECONDS = _tickets_store_module.REPLACE_RETRY_SECONDS
RUN_IDENTITY_NAME = _tickets_store_module.RUN_IDENTITY_NAME
RUN_LOCKS_DIR = _tickets_store_module.RUN_LOCKS_DIR
RUN_NOTES_NAME = _tickets_store_module.RUN_NOTES_NAME
RUN_STATE_TREES = _tickets_store_module.RUN_STATE_TREES
SINK_CONVENTION = _tickets_store_module.SINK_CONVENTION
UTC_STAMP = _tickets_store_module.UTC_STAMP
_create_text_exclusively = _tickets_store_module._create_text_exclusively
_cwd = _tickets_store_module._cwd
_executor_script = _tickets_store_module._executor_script
_find_repo_root = _tickets_store_module._find_repo_root
_identity_document = _tickets_store_module._identity_document
_identity_update = _tickets_store_module._identity_update
_improvement_root = _tickets_store_module._improvement_root
def _installed_orchflows_metadata() -> dict:
    """Return the installed library identity through its store owner."""
    return _tickets_store_module._installed_orchflows_metadata()
_iter_run_dirs = _tickets_store_module._iter_run_dirs
_load_ticket = _tickets_store_module._load_ticket
_main_checkout_root = _tickets_store_module._main_checkout_root
_normalized_origin = _tickets_store_module._normalized_origin
_origin_url = _tickets_store_module._origin_url
_project_key = _tickets_store_module._project_key
_read_identity = _tickets_store_module._read_identity
_replace_atomically = _tickets_store_module._replace_atomically
_run_lock = _tickets_store_module._run_lock
_run_state_root = _tickets_store_module._run_state_root
_runs_root = _tickets_store_module._runs_root
_same_project = _tickets_store_module._same_project
_segment_error = _tickets_store_module._segment_error
REPAIR_RUN_IDENTITY_USAGE = _tickets_store_module.REPAIR_RUN_IDENTITY_USAGE
_cmd_repair_run_identity = _tickets_store_module._cmd_repair_run_identity
def _terminal_identity_update(run: str, ticket_id: str, status: str, now):
    """Return the terminal identity update through its store owner."""
    return _tickets_store_module._terminal_identity_update(run, ticket_id, status, now)
_tickets_root = _tickets_store_module._tickets_root
_waiting_out_windows = _tickets_store_module._waiting_out_windows
_workspace_root = _tickets_store_module._workspace_root
_write_identity = _tickets_store_module._write_identity
_write_text_atomically = _tickets_store_module._write_text_atomically
_writer_identity = _tickets_store_module._writer_identity
normalized_isolation = _tickets_store_module.normalized_isolation
INDEPENDENCE_VALUES = _tickets_issue_module.INDEPENDENCE_VALUES
ISOLATION_VALUES = _tickets_issue_module.ISOLATION_VALUES
NEW_DEFAULT_BOUND = _tickets_issue_module.NEW_DEFAULT_BOUND
NEW_USAGE = _tickets_issue_module.NEW_USAGE
_cmd_new = _tickets_issue_module._cmd_new
_frontmatter_list = _tickets_issue_module._frontmatter_list
_issue_ticket = _tickets_issue_module._issue_ticket
_render_ticket = _tickets_issue_module._render_ticket
CHECKABLE_STATUSES = _tickets_lifecycle_module.CHECKABLE_STATUSES
CHECK_USAGE = _tickets_lifecycle_module.CHECK_USAGE
SET_STATUS_USAGE = _tickets_lifecycle_module.SET_STATUS_USAGE
_check_under_run_lock = _tickets_lifecycle_module._check_under_run_lock
_claim_is_stale = _tickets_assignment_module._claim_is_stale
_cmd_check = _tickets_lifecycle_module._cmd_check
_cmd_dispatch_open = _tickets_attempts_module._cmd_dispatch_open
_cmd_dispatch_commit = _tickets_attempts_module._cmd_dispatch_commit
_cmd_dispatch_retire = _tickets_attempts_module._cmd_dispatch_retire
_cmd_dispatch_replace = _tickets_attempts_module._cmd_dispatch_replace
_cmd_dispatch_join = _tickets_join_module._cmd_dispatch_join
_cmd_dispatch_outcome = _tickets_outcome_module._cmd_dispatch_outcome
LAND_USAGE = _tickets_land_module.LAND_USAGE
_cmd_land = _tickets_land_module._cmd_land
_cmd_list = _tickets_lifecycle_module._cmd_list
_cmd_ready = _tickets_lifecycle_module._cmd_ready
_cmd_set_status = _tickets_lifecycle_module._cmd_set_status
_cmd_show = _tickets_lifecycle_module._cmd_show
_set_status_under_run_lock = _tickets_lifecycle_module._set_status_under_run_lock
ASSIGNMENT_SECTIONS = _tickets_assignment_module.ASSIGNMENT_SECTIONS
dispatch_assignment = _tickets_assignment_module.dispatch_assignment
COVERAGE_RECORD_NAME = _tickets_result_module.COVERAGE_RECORD_NAME
IMPROVEMENT_USAGE = _tickets_result_module.IMPROVEMENT_USAGE
PROPOSALS_DIR = _tickets_result_module.PROPOSALS_DIR
RESULT_USAGE = _tickets_result_module.RESULT_USAGE
RUN_STATE_USAGE = _tickets_result_module.RUN_STATE_USAGE
TERMINAL_HEADING = _tickets_result_module.TERMINAL_HEADING
_append_one_line = _tickets_result_module._append_one_line
_cmd_result = _tickets_result_module._cmd_result
_cmd_run_state = _tickets_result_module._cmd_run_state
_is_terminal_heading = _tickets_result_module._is_terminal_heading
_notes_terminal = _tickets_result_module._notes_terminal
_result_under_run_lock = _tickets_result_module._result_under_run_lock
_run_state_under_run_lock = _tickets_result_module._run_state_under_run_lock
ITERATION_ID_RE = _tickets_worklog_module.ITERATION_ID_RE
WORKLOG_NAME = _tickets_worklog_module.WORKLOG_NAME
WORKLOG_RENDER_MARKER = _tickets_worklog_module.WORKLOG_RENDER_MARKER
WORKLOG_SECTIONS = _tickets_worklog_module.WORKLOG_SECTIONS
WORKLOG_USAGE = _tickets_worklog_module.WORKLOG_USAGE
_claim_order = _tickets_worklog_module._claim_order
_cmd_worklog = _tickets_worklog_module._cmd_worklog
_packs_root = _tickets_worklog_module._packs_root
_quoted = _tickets_worklog_module._quoted
_render_worklog = _tickets_worklog_module._render_worklog
_run_goal = _tickets_worklog_module._run_goal
_run_tickets = _tickets_worklog_module._run_tickets
_upstream = _tickets_worklog_module._upstream
_write_rendered_worklog = _tickets_worklog_module._write_rendered_worklog
GRADE_USAGE = _tickets_commands_module.GRADE_USAGE
DISPATCH_USAGE = _tickets_commands_module.DISPATCH_USAGE
HELP_COMMANDS = _tickets_commands_module.HELP_COMMANDS
HELP_FLAGS = _tickets_commands_module.HELP_FLAGS
SUBCOMMAND_SUMMARY = _tickets_commands_module.SUBCOMMAND_SUMMARY
SUBCOMMAND_USAGE = _tickets_commands_module.SUBCOMMAND_USAGE
VALUE_FLAGS = _tickets_commands_module.VALUE_FLAGS
read_payload = _tickets_commands_module.read_payload
resolve_payload_flags = _tickets_commands_module.resolve_payload_flags
LINT_USAGE = _tickets_lint_module.LINT_USAGE
apply_fixes = _tickets_lint_module.apply_fixes
lint_findings = _tickets_lint_module.lint_findings
_cmd_lint = _tickets_lint_module._cmd_lint
_cmd_grade = _tickets_dispatch_module._cmd_grade
_cmd_dispatch = _tickets_dispatch_module._cmd_dispatch
_cmd_help = _tickets_dispatch_module._cmd_help
_cmd_improvement = _tickets_dispatch_module._cmd_improvement
_dispatch = _tickets_dispatch_module._dispatch
_help_requested = _tickets_dispatch_module._help_requested
main = _tickets_dispatch_module.main
console = _tickets_dispatch_module.console
state_root = _tickets_store_module.state_root
datetime = _tickets_store_module.datetime
timezone = _tickets_store_module.timezone
time = _tickets_store_writes_module.time
msvcrt = _tickets_store_writes_module.msvcrt
fcntl = _tickets_store_writes_module.fcntl
json = _tickets_store_module.json
re = _tickets_format_module.re
sys = _tickets_dispatch_module.sys
tempfile = _tickets_store_writes_module.tempfile
contextmanager = _tickets_store_module.contextmanager
Path = _tickets_store_module.Path

def _sync_seams():
    _tickets_store_writes_module.REPLACE_BUDGET_SECONDS = REPLACE_BUDGET_SECONDS
    _tickets_store_writes_module.REPLACE_RETRY_SECONDS = REPLACE_RETRY_SECONDS
    _tickets_store_module._cwd = _cwd
    _tickets_store_module.datetime = datetime
    _tickets_lifecycle_module.datetime = datetime
    _tickets_issue_module.datetime = datetime
    _tickets_result_module.datetime = datetime
    _tickets_dispatch_module.datetime = datetime
    _tickets_store_writes_module.msvcrt = msvcrt
    _tickets_result_module.msvcrt = msvcrt
    _tickets_store_module._write_identity = _write_identity
    _tickets_issue_module._write_identity = _write_identity
    _tickets_lifecycle_module._write_identity = _write_identity
    _tickets_result_module._write_identity = _write_identity
    _tickets_dispatch_module._write_identity = _write_identity
    _tickets_store_module._write_text_atomically = _write_text_atomically
    _tickets_lifecycle_module._write_text_atomically = _write_text_atomically
    _tickets_result_module._write_text_atomically = _write_text_atomically
    _tickets_result_module._append_one_line = _append_one_line
    _tickets_dispatch_module._cmd_new = _cmd_new
    _tickets_dispatch_module._cmd_dispatch_open = _cmd_dispatch_open
    _tickets_dispatch_module._cmd_dispatch = _cmd_dispatch
    _tickets_dispatch_module._cmd_dispatch_commit = _cmd_dispatch_commit
    _tickets_dispatch_module._cmd_dispatch_retire = _cmd_dispatch_retire
    _tickets_dispatch_module._cmd_dispatch_replace = _cmd_dispatch_replace
    _tickets_dispatch_module._cmd_dispatch_join = _cmd_dispatch_join
    _tickets_dispatch_module._cmd_dispatch_outcome = _cmd_dispatch_outcome
    _tickets_dispatch_module._cmd_land = _cmd_land
    _tickets_dispatch_facade_module._cmd_ready = _cmd_ready
    _tickets_dispatch_facade_module._cmd_dispatch_open = _cmd_dispatch_open
    _tickets_dispatch_facade_module._cmd_dispatch_retire = _cmd_dispatch_retire
    _tickets_attempts_module._write_text_atomically = _write_text_atomically
    _tickets_dispatch_module._cmd_ready = _cmd_ready
    _tickets_dispatch_module._cmd_show = _cmd_show
    _tickets_dispatch_module._cmd_check = _cmd_check
    _tickets_dispatch_module._cmd_set_status = _cmd_set_status
    _tickets_dispatch_module._cmd_result = _cmd_result
    _tickets_dispatch_module._cmd_worklog = _cmd_worklog
    _tickets_dispatch_module._cmd_run_state = _cmd_run_state
    _tickets_dispatch_module._cmd_lint = _cmd_lint
    _tickets_dispatch_module._cmd_bound_check = _cmd_bound_check
    _tickets_lint_module._write_text_atomically = _write_text_atomically

# Handed down, never fetched back up: the dispatcher calls this once per
# invocation and no helper imports this facade to reach it.
_tickets_dispatch_module._sync_seams = _sync_seams

if __name__ == "__main__":
    raise SystemExit(console.run(main))
