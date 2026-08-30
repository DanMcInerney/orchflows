"""Template instantiation and the generation stamp that opens a cut.

Both write a whole graph in one act, and both were carried by the
dispatcher beside the subcommand table until that file reached its source
ceiling.  They sit together here because they share the one question --
what a run's members are before any of them is dispatched -- and because
`stamp-generation` is `instantiate`'s hand-authored twin: one seals a graph
it rendered, the other opens the lifecycle on a graph somebody wrote.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from datetime import datetime, timezone

if __package__:
    from .tickets_format import (
        GATE_ID_MARKER, PLACEHOLDER_RE, ROOT_EXECUTOR, TEMPLATE_FILE,
        _executor_of, _extract_all, _extract_flag, _parse_frontmatter,
        _read_utf8, _set_frontmatter_field, ticket_defects,
    )
    from .tickets_store import (
        NO_SINK_ERROR, _create_text_exclusively, _identity_update, _load_ticket,
        _run_lock, _runs_root, _segment_error, _tickets_root, _write_identity,
        _write_text_atomically,
    )
    from .tickets_admission import dependency_order_findings
    from .tickets_worklog import _template_order
    from .tickets_emission import grade_run_emission
    from .tickets_context import run_snapshot
    from .tickets_generations import (
        GENERATION_RE, _root_payload, canonical_json, draft_snapshot,
        generation_identity, seal_assignments, validate_draft,
    )
    from .tickets_transitions import pending_admission, stamp
    from .tickets_commands import INSTANTIATE_USAGE, STAMP_GENERATION_USAGE
    from .tickets_root_reservation import mismatch as _root_reservation_mismatch
else:  # pragma: no cover - direct/installed flat script path
    from tickets_format import (
        GATE_ID_MARKER, PLACEHOLDER_RE, ROOT_EXECUTOR, TEMPLATE_FILE,
        _executor_of, _extract_all, _extract_flag, _parse_frontmatter,
        _read_utf8, _set_frontmatter_field, ticket_defects,
    )
    from tickets_store import (
        NO_SINK_ERROR, _create_text_exclusively, _identity_update, _load_ticket,
        _run_lock, _runs_root, _segment_error, _tickets_root, _write_identity,
        _write_text_atomically,
    )
    from tickets_admission import dependency_order_findings
    from tickets_worklog import _template_order
    from tickets_emission import grade_run_emission
    from tickets_context import run_snapshot
    _generations = __import__('tickets_generations')
    GENERATION_RE = _generations.GENERATION_RE
    _root_payload = _generations._root_payload
    canonical_json = _generations.canonical_json
    draft_snapshot = _generations.draft_snapshot
    generation_identity = _generations.generation_identity
    seal_assignments = _generations.seal_assignments
    validate_draft = _generations.validate_draft
    from tickets_transitions import pending_admission, stamp
    from tickets_commands import INSTANTIATE_USAGE, STAMP_GENERATION_USAGE
    _root_reservation_mismatch = __import__('tickets_root_reservation').mismatch


def git_head():
    done = subprocess.run(["git", "rev-parse", "HEAD"], text=True, capture_output=True)
    return done.stdout.strip() if done.returncode == 0 else None


def render_stub(text: str, values: dict):
    missing = []
    def replace(match):
        name = match.group(1).strip()
        if name not in values:
            missing.append(name)
            return match.group(0)
        return str(values[name])
    rendered = PLACEHOLDER_RE.sub(replace, text)
    return (rendered, None if not missing else "unfilled placeholders: " + ", ".join(sorted(set(missing))))
def _template_stubs(directory: Path, values: dict):
    """``(stubs, error)`` — every stub in the template, substituted and graded.
    ``stubs`` maps a stub id to its text and its dependency ids, in file
    order. Each stub is substituted first and graded after, because a
    placeholder standing where an executor or a bound belongs is a defect
    only until it is filled.
    """
    paths = sorted((path for path in directory.glob('*.md') if path.name != TEMPLATE_FILE))
    if not paths:
        return (None, {'error': f'template {directory} holds no stub: a template is {TEMPLATE_FILE} plus one or more <id>.md ticket stubs'})
    stubs = {}
    sources = []
    for path in paths:
        text, failure = _read_utf8(path, f'stub {path.name}')
        if failure is not None:
            return (None, failure)
        sources.append((path, text))
    for path, text in sources:
        text, render_error = render_stub(text, values)
        if render_error is not None:
            return (None, {'error': f'stub {path.stem} carries {render_error}'})
        defects = ticket_defects(text, stub=True)
        if defects:
            return (None, {'error': f'stub {path.stem} is off contract (contracts/work-item.md): ' + '; '.join(defects)})
        data = _parse_frontmatter(text)
        declared_id = str(data.get('id') or '').strip()
        if declared_id != path.stem:
            return (None, {'error': f"stub {path.name} names id '{declared_id}': a stub's id is its file stem, and `depends_on` names ids"})
        # The same refusal draft validation makes, at the same authoring
        # door: `_sealed_template_snapshot` seals through the generation
        # algebra without passing `_draft_findings`, so a template stub whose
        # `depends_on` was written out of order sealed as a second digest for
        # the one edge set and nothing said so.
        unordered = dependency_order_findings(path.stem, data)
        if unordered:
            return (None, {'error': f"stub {path.name} is off contract (contracts/work-item.md): {unordered[0]['detail']}", 'findings': unordered})
        stubs[path.stem] = (text, list(data.get('depends_on') or []))
    return (stubs, None)


def _sealed_template_snapshot(run: str, ordered: list, rendered: list):
    """Seal one instantiated graph through the canonical generation algebra."""

    snapshot = {path.stem: text for path, text in rendered}
    root_id = ordered[0]
    members = ordered[1:]
    draft = draft_snapshot(root_id, snapshot, 1, members)
    receipt = validate_draft(root_id, snapshot, draft, members)
    sealed = seal_assignments(root_id, snapshot, draft, receipt, members)
    match = GENERATION_RE.fullmatch(draft["cut_generation"])
    if match is None:
        raise ValueError("template generation identity is malformed")
    generation_root = _runs_root()
    if generation_root is None:
        raise ValueError(NO_SINK_ERROR)
    generation_dir = generation_root / run / "generations"
    validated_path = generation_dir / f"{match.group(4)}.validated.json"
    sealed_path = generation_dir / f"{match.group(4)}.sealed.json"
    seals = {
        ticket_id: _parse_frontmatter(sealed[ticket_id]).get("assignment_seal")
        for ticket_id in ordered
    }
    validated = canonical_json({"draft": draft, "receipt": receipt}) + "\n"
    record = canonical_json({
        "assignment_seals": seals,
        "cut_generation": draft["cut_generation"],
        "receipt": receipt,
        "root_generation": draft["root_generation"],
        "root_id": root_id,
        "state": "sealed",
    }) + "\n"
    return (
        [(path, sealed[path.stem]) for path, _ in rendered],
        ((validated_path, validated), (sealed_path, record)),
        {"root_id": root_id, "root_generation": draft["root_generation"], "cut_generation": draft["cut_generation"]},
    )


def _cmd_instantiate(rest):
    """Instantiate one template into one run's tickets.
    A template is a directory: ``template.md`` and one file per stub. What
    happens here is substitution, the same grading every issued ticket gets,
    the graph checks a directory of files cannot carry (edges, a cycle, the
    single terminal), and then one write per stub — in that order, so a
    template refused for its last stub has written none of the others.
    """
    args = list(rest)
    run = _extract_flag(args, '--run')
    settings = _extract_all(args, '--set')
    stray = next((arg for arg in args if arg.startswith('-')), None)
    if stray is not None:
        return {'error': f'instantiate does not accept {stray}. usage: {INSTANTIATE_USAGE}'}
    if len(args) != 1:
        return {'error': f'usage: {INSTANTIATE_USAGE}'}
    if run is None:
        return {'error': f'instantiate requires --run <run>. usage: {INSTANTIATE_USAGE}'}
    invalid = _segment_error('run id', run)
    if invalid is not None:
        return invalid
    directory = Path(args[0])
    if not directory.is_dir():
        return {'error': f'template directory not found: {directory}'}
    template_path = directory / TEMPLATE_FILE
    if not template_path.is_file():
        return {'error': f"template directory {directory} has no {TEMPLATE_FILE}: it declares the template's name, entry and placeholders"}
    values = {}
    for setting in settings:
        key, separator, value = setting.partition('=')
        if not separator or not key.strip():
            return {'error': f"--set takes k=v: '{setting}' names no value. usage: {INSTANTIATE_USAGE}"}
        values[key.strip()] = value
    manifest, failure = _read_utf8(template_path, TEMPLATE_FILE)
    if failure is not None:
        return failure
    template = _parse_frontmatter(manifest)
    declared = template.get('placeholders')
    declared = declared if isinstance(declared, list) else []
    builtins = {'run': run}
    baseline = git_head()
    if baseline is not None:
        builtins['baseline'] = baseline
    # A declared builtin is supplied, not unsupplied. `run` and `baseline`
    # are this command's to fill, and a stub that names one must be able to
    # declare it: every `{{name}}` a stub uses has to appear in the
    # manifest's `placeholders` (tools/validate_support/structure.py), so
    # without this a template could use a builtin or validate, never both.
    unsupplied = [name for name in declared if name not in values and name not in builtins]
    if unsupplied:
        return {'error': f'{TEMPLATE_FILE} declares the placeholders {unsupplied} that no --set supplies'}
    stubs, error = _template_stubs(directory, {**values, **builtins})
    if error is not None:
        return error
    ordered, error = _template_order(stubs)
    if error is not None:
        return error
    tickets_root = _tickets_root()
    if tickets_root is None:
        return {'error': NO_SINK_ERROR}
    run_dir = tickets_root / run
    rendered = []
    for stub_id in ordered:
        text, dependencies = stubs[stub_id]
        entry = stamp('stamp')
        text = _set_frontmatter_field(text, 'run', run)
        text = _set_frontmatter_field(text, 'status', entry.status)
        text = _set_frontmatter_field(text, 'admission', entry.admission)
        for field in entry.blanks:
            text = _set_frontmatter_field(text, field, '')
        path = run_dir / f'{stub_id}.md'
        if GATE_ID_MARKER in stub_id:
            return {'error': f"template stub id '{stub_id}' is reserved for `tickets.py gate`; a template cannot assemble a partial or alternate gate family. Nothing was written"}
        rendered.append((path, text))
    try:
        rendered, generation_documents, generation_stamp = _sealed_template_snapshot(run, ordered, rendered)
    except (OSError, UnicodeDecodeError, ValueError) as error:
        return {'error': f'template generation could not be sealed: {error}. Nothing was written'}
    incoming_roots = [path.stem for path, text in rendered if _executor_of(_parse_frontmatter(text)) == ROOT_EXECUTOR]
    written = []
    generation_written = []
    try:
        with _run_lock(run):
            for path, _ in rendered:
                if path.exists():
                    return {'error': f"ticket id '{path.stem}' is already issued in run '{run}': {path}. Nothing was written"}
            existing_roots = []
            for path in sorted(run_dir.glob('*.md')) if run_dir.is_dir() else []:
                loaded = _load_ticket(path)
                if 'error' not in loaded and _executor_of(loaded) == ROOT_EXECUTOR:
                    existing_roots.append(str(loaded.get('id') or path.stem))
            if existing_roots and incoming_roots:
                return {'error': f"run '{run}' would have root tickets {existing_roots + incoming_roots}: one physical run has one root and one composite gate. Nothing was written"}
            emission = grade_run_emission('instantiate', run, run_dir, {path.stem: text for path, text in rendered})
            if emission is not None:
                return {**emission, 'error': emission['error'] + '. Nothing was written'}
            identity_dir, identity, refusal = _identity_update(run, datetime.now(timezone.utc))
            if refusal is not None:
                return refusal
            run_dir.mkdir(parents=True, exist_ok=True)
            for path, text in rendered:
                _create_text_exclusively(path, text)
                written.append(path)
            for path, text in generation_documents:
                path.parent.mkdir(parents=True, exist_ok=True)
                _create_text_exclusively(path, text)
                generation_written.append(path)
            if identity is not None:
                identity_dir.mkdir(parents=True, exist_ok=True)
                _write_identity(identity_dir, identity)
    except OSError as error:
        for path in written:
            path.unlink(missing_ok=True)
        for path in generation_written:
            path.unlink(missing_ok=True)
        return {'error': f'unwritable ticket: {error}. Nothing was written'}
    return {'instantiate': {'template': str(template.get('name') or directory.name), 'run': run, 'ids': ordered, 'paths': [str(path) for path, _ in rendered], 'generation': generation_stamp}}
def _cmd_stamp_generation(rest):
    """Open the generation lifecycle on one root and its declared cut.

    It sits beside `instantiate` rather than in `tickets_generations`
    because that module is the generation algebra and is at its source
    ceiling; what it exports is called, not extended.

    The identity comes from the exact snapshot, so a stamp is reproducible
    from what it stamped. Root kind is independent of its executor: direct
    and decomposed roots enter the same lifecycle.

    Refused on a cut any member of which is already taken up -- a stamp
    rewrites the assignment a member is graded against, and doing that
    under a working executor is the moving target rules/verification.md §3
    forbids.
    """
    args = list(rest)
    if len(args) != 2:
        return {'error': f'usage: {STAMP_GENERATION_USAGE}'}
    run, root_id = args
    for kind, value in (('run id', run), ('ticket id', root_id)):
        invalid = _segment_error(kind, value)
        if invalid is not None: return invalid
    tickets_root = _tickets_root()
    if tickets_root is None:
        return {'error': NO_SINK_ERROR}
    run_dir = tickets_root / run
    try:
        with _run_lock(run):
            runs_root = _runs_root()
            if runs_root is None:
                return {'error': NO_SINK_ERROR}
            reservation_error = _root_reservation_mismatch(
                runs_root, run, root_id,
            )
            if reservation_error is not None:
                return {'error': reservation_error}
            snapshot, unreadable = run_snapshot(run_dir) if run_dir.is_dir() else ({}, [])
            if unreadable:
                return {'error': f'unreadable ticket: {unreadable[0][0]}'}
            if root_id not in snapshot:
                return {'error': f'root ticket not found in exact snapshot: {root_id}'}
            members = [root_id] + sorted(i for i in snapshot if i.startswith(root_id + '.'))
            for member_id in members:
                data = _parse_frontmatter(snapshot[member_id])
                status = str(data.get('status') or '')
                if status not in ('pending', 'ready') or str(data.get('claimed_by') or '').strip():
                    return {'error': f"stamp-generation refused: {run}/{member_id} is '{status or '<missing>'}', and a stamp rewrites the assignment it would be working against (rules/verification.md §3). Nothing was written"}
                if str(data.get('root_generation') or '').strip():
                    return {'error': f'stamp-generation refused: {run}/{member_id} already carries a generation; the lifecycle is opened once. Nothing was written'}
            identity = generation_identity('root', root_id, 1, _root_payload(root_id, snapshot))
            stamped = {}
            for member_id in members:
                text = _set_frontmatter_field(snapshot[member_id], 'root_generation', identity)
                text = _set_frontmatter_field(text, 'admission', pending_admission())
                stamped[member_id] = text
            emission = grade_run_emission('stamp-generation', run, run_dir, stamped, repairs=True)
            if emission is not None:
                return {**emission, 'error': emission['error'] + '. Nothing was written'}
            written = {}
            try:
                for member_id, text in stamped.items():
                    written[member_id] = snapshot[member_id]
                    _write_text_atomically(run_dir / f'{member_id}.md', text)
            except OSError:
                for member_id, text in written.items():
                    _write_text_atomically(run_dir / f'{member_id}.md', text)
                raise
    except (OSError, UnicodeDecodeError, ValueError) as error:
        return {'error': str(error)}
    return {'stamp_generation': {'root_generation': identity, 'run': run, 'root_id': root_id, 'ids': members, 'state': 'drafting'}}


__all__ = (
    "_cmd_instantiate", "_cmd_stamp_generation", "_sealed_template_snapshot",
    "_template_stubs", "git_head", "render_stub",
)
