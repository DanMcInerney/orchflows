"""Assemble all findings for one issued ticket."""

import importlib

try:  # repository checkout
    from scripts import cutcheck_contract as _contract
except ImportError:  # installed flat script directory
    import cutcheck_contract as _contract
BYTECODE_RE = _contract.BYTECODE_RE
BYTECODE_REPAIR = _contract.BYTECODE_REPAIR
BYTECODE_WRITTEN = _contract.BYTECODE_WRITTEN
COMPLETION_SECTION = _contract.COMPLETION_SECTION
EXTRACTION_GAP = _contract.EXTRACTION_GAP
INPUTS_SECTION = _contract.INPUTS_SECTION
MISSING_PATH = _contract.MISSING_PATH
OBJECTIVE_SECTION = _contract.OBJECTIVE_SECTION
PRE_EXISTING = _contract.PRE_EXISTING
UNCONFINED_ORACLE = _contract.UNCONFINED_ORACLE
VERDICT_IN_OUTPUT = _contract.VERDICT_IN_OUTPUT
WHOLE_SUITE_ORACLE = _contract.WHOLE_SUITE_ORACLE
_MUTATED = _contract._MUTATED
_parse_frontmatter = _contract._parse_frontmatter
_sections = _contract._sections
FAMILY_OF = _contract.FAMILY_OF
FAMILY_2 = _contract.FAMILY_2
FAMILY_3 = _contract.FAMILY_3

try:  # repository checkout
    from scripts.tickets_format import adapter_id
except ImportError:  # installed flat script directory
    from tickets_format import adapter_id

try:  # repository checkout
    from scripts import cutcheck_commands as _commands_module
except ImportError:  # installed flat script directory
    import cutcheck_commands as _commands_module
_commands = _commands_module._commands
_criteria = _commands_module._criteria
_oracle_class = _commands_module._oracle_class
_shape = _commands_module._shape
_stated_provenance = _commands_module._stated_provenance

try:  # repository checkout
    from scripts import cutcheck_scope as _scope
except ImportError:  # installed flat script directory
    import cutcheck_scope as _scope
_covered = _scope._covered
_granted = _scope._granted
_path_args = _scope._path_args
_path_reality = _scope._path_reality
_prose = _scope._prose
_scope_closure = _scope._scope_closure
_scope_open = _scope._scope_open

try:  # repository checkout
    from scripts import cutcheck_execute as _execute
except ImportError:  # installed flat script directory
    import cutcheck_execute as _execute
_discrimination = _execute._discrimination

try:  # repository checkout
    from scripts import cutcheck_search as _search
except ImportError:  # installed flat script directory
    import cutcheck_search as _search
_verdict_in_output = _search._verdict_in_output
_whole_suite = _search._whole_suite

try:  # repository checkout
    from scripts.cutcheck_graph import _root_ids
except ImportError:  # installed flat script directory
    from cutcheck_graph import _root_ids


def _policy_findings(ticket_id, text, sibling_texts, baseline_tree, head_tree):
    """Render lower identity/scope validator codes unchanged in cutcheck."""
    rendered = []
    data = _parse_frontmatter(text)
    common = {
        'ticket_id': ticket_id,
        'text': text,
        'siblings': sibling_texts,
        'adapter_id': adapter_id(data.get('pack')),
        'context': {'baseline_tree': baseline_tree, 'head_tree': head_tree},
    }
    package = __package__.rsplit('.', 1)[0] if __package__ and '.' in __package__ else __package__
    for module_name, function_name, family in (
        ('tickets_inputs', 'grade_inputs', FAMILY_2),
        ('tickets_scope', 'grade_scope', FAMILY_3),
    ):
        qualified = f'{package}.{module_name}' if package else module_name
        try:
            module = importlib.import_module(qualified)
        except ModuleNotFoundError as error:
            if error.name in (qualified, module_name):
                continue
            raise
        probe = getattr(module, function_name, None)
        if not callable(probe):
            continue
        result = probe(**common)
        for item in result.get('findings', []) if isinstance(result, dict) else []:
            code = str(item.get('code') or 'validator-finding')
            FAMILY_OF.setdefault(code, family)
            field = str(item.get('field') or module_name)
            detail = str(item.get('detail') or '')
            rendered.append((ticket_id, 0, code, f'{field}: {detail}'))
    return rendered

def _check_ticket(path, baseline_tree, head_tree, siblings):
    text = path.read_text(encoding="utf-8")
    frontmatter = _parse_frontmatter(text)
    ticket_id = frontmatter.get("id") or path.stem
    sections = _sections(text)
    granted = _granted(frontmatter, siblings)
    sibling_texts = {}
    for sibling_path in sorted(path.parent.glob('*.md')):
        sibling_text = sibling_path.read_text(encoding='utf-8')
        sibling_data = _parse_frontmatter(sibling_text)
        sibling_texts[str(sibling_data.get('id') or sibling_path.stem)] = sibling_text
    findings = _policy_findings(ticket_id, text, sibling_texts, baseline_tree, head_tree)
    # A top-level root freezes acceptance; it is not one of the unit artifacts
    # that acceptance issues.  Keep the identity and scope policy grades above,
    # but do not reinterpret the root's read-only invariants as unit paths or
    # writes.  Use the graph's positional definition so a nested decomposer
    # receives no root exemption.
    if ticket_id in _root_ids(siblings):
        return findings
    for number, criterion in _criteria(sections.get(COMPLETION_SECTION, "")):
        prose = _prose(criterion)
        findings.extend(
            (ticket_id, number, klass, detail)
            for klass, detail in _path_reality(prose, baseline_tree)
        )
        commands = _commands(criterion)
        if not commands:
            # The stated class travels with the gap: a judged criterion states
            # no command by design, and one that names a class this tool can
            # run is under-coverage. The decomposer reads which it has.
            klass = _oracle_class(criterion)
            detail = criterion[:100]
            if klass:
                detail = "{} | oracle_class: {}".format(detail, klass)
            findings.append((ticket_id, number, EXTRACTION_GAP, detail))
            continue
        invariant = _stated_provenance(criterion) == PRE_EXISTING
        for command in commands:
            shape = _shape(command)
            if shape:
                # Reported and never run: a swallowed pipeline cannot be run
                # argv-only anyway, and an unconfined git span must not be.
                # This `continue` is the refusal -- everything below executes.
                findings.extend((ticket_id, number, k, command) for k in shape)
                continue
            missing = [
                arg
                for arg in _path_args(command)
                if not (baseline_tree / arg).exists() and not _covered(arg, granted)
            ]
            if missing:
                # A command reaching for a path nothing has is not discriminating.
                findings.extend(
                    (ticket_id, number, MISSING_PATH, "{}: {}".format(arg, command))
                    for arg in missing
                )
                continue
            if _verdict_in_output(command):
                findings.append((ticket_id, number, VERDICT_IN_OUTPUT, command))
                continue
            if invariant:
                # An oracle the criterion states is pre-existing is an
                # invariant: it passed before this work and has to pass after,
                # so discriminating is not its job and never was.
                continue
            if _whole_suite(command, baseline_tree):
                # Below the stamp, because an invariant is not being asked to
                # discriminate, and above execution because this one must not
                # run: the mandated `discover` that lands here outgrows
                # COMMAND_TIMEOUT, and the timeout reports the clock.
                findings.append((ticket_id, number, WHOLE_SUITE_ORACLE, command))
                continue
            del _MUTATED[:]
            klass = _discrimination(command, baseline_tree, head_tree)
            # Named once per path however many graded copies the span wrote
            # into: two revisions of one repository are one span's worth of
            # defect, not two.
            wrote = sorted(set(_MUTATED))
            bytecode = [path for path in wrote if BYTECODE_RE.search(path)]
            findings.extend(
                (ticket_id, number, UNCONFINED_ORACLE, "{}: {}".format(path, command))
                for path in wrote
                if path not in bytecode
            )
            if bytecode:
                findings.append(
                    (
                        ticket_id,
                        number,
                        BYTECODE_WRITTEN,
                        "{}: {}: {}".format(
                            ", ".join(bytecode), BYTECODE_REPAIR, command
                        ),
                    )
                )
            if klass is not None:
                findings.append((ticket_id, number, klass, command))
    header = "\n".join(
        sections.get(name, "") for name in (OBJECTIVE_SECTION, INPUTS_SECTION)
    )
    findings.extend(
        (ticket_id, 0, klass, detail)
        for klass, detail in _path_reality(_prose(header), baseline_tree)
    )
    body = "\n".join(
        sections.get(name, "") for name in (OBJECTIVE_SECTION, COMPLETION_SECTION)
    )
    findings.extend(
        (ticket_id, 0, klass, detail)
        for klass, detail in _scope_closure(frontmatter, _prose(body))
    )
    findings.extend(
        (ticket_id, 0, klass, detail)
        for klass, detail in _scope_open(
            frontmatter, _prose(sections.get(OBJECTIVE_SECTION, "")), baseline_tree
        )
    )
    return findings


# What the caller reads off the status, and what the status does not mean. The
# six families are the module docstring's to describe; this names none of them.

__all__ = (
    '_check_ticket', '_policy_findings',
)
