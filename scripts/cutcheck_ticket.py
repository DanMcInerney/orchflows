"""Assemble all findings for one issued ticket, and own the four cut screens.

The screens are family 3's, and they live here rather than beside the closure
readings because that module stands at its own size ceiling; the assembly this
module already does is what calls them, so nothing crosses a module boundary to
reach them. Each is one sentence:

1. ``_policy_scope`` -- a fixed-input policy ordering a write the grant does
   not cover. Family 3 graded the Objective and the Completion test, which
   commit the item, and never the Fixed inputs, which order it.
2. ``_consumer_census`` -- the checks under ``tests/`` that assert, word for
   word, a phrase the objective is ordered to delete. ``_scope_open`` reads the
   single token a removal names; this reads the sentence, and refuses where
   that one is advisory, because a check holding the deleted text fails the
   moment the item lands and the item may not repair it.
3. ``_removal_evidence`` -- a removal argued from reachability with no probe
   among the fixed inputs. Write-path-unreachable is not dead.
4. ``_marker_only_relocation`` -- a relocation graded by substring markers
   alone, which see the words arrive and cannot see what they mean. Advisory,
   and reported by nobody yet: the advisory set is a frozen contract constant
   whose membership one ungranted suite pins exactly, so this judgment is
   decided here and wired at the repair that may widen that set.

The first three report outside the advisory set and move the exit status.
"""

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
_indirect_whole_suite = _search._indirect_whole_suite
_input_literals = _search._input_literals

try:  # repository checkout
    from scripts.cutcheck_graph import _root_ids
except ImportError:  # installed flat script directory
    from cutcheck_graph import _root_ids

try:  # repository checkout
    from scripts import cutcheck_pricing as _pricing
except ImportError:  # installed flat script directory
    import cutcheck_pricing as _pricing
# Family 3's other six, which read what a cut costs rather than what it says.
# Their classes register themselves from that module; these names are re-exported
# so a reader reaches every family 3 screen through the assembly that calls them.
UNPRICED_GROWTH = _pricing.UNPRICED_GROWTH
UNSPLITTABLE_OWNER = _pricing.UNSPLITTABLE_OWNER
CEILING_WITHOUT_ARITHMETIC = _pricing.CEILING_WITHOUT_ARITHMETIC
UNPINNED_OUTPUT = _pricing.UNPINNED_OUTPUT
PACK_INADMISSIBLE_ROOT = _pricing.PACK_INADMISSIBLE_ROOT
EXCLUDED_REQUIRED_COMMAND = _pricing.EXCLUDED_REQUIRED_COMMAND


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

POLICY_OUTSIDE_SCOPE = "policy-outside-scope"
UNGRANTED_CONSUMER = "ungranted-consumer"
UNPROBED_REMOVAL = "unprobed-removal"
MARKER_ONLY_RELOCATION = "marker-only-relocation"
for _screen in (POLICY_OUTSIDE_SCOPE, UNGRANTED_CONSUMER, UNPROBED_REMOVAL,
                MARKER_ONLY_RELOCATION):
    # Registered from the judgment's own module, the way `_policy_findings`
    # registers a validator's classes. `setdefault`, so a contract that adopts
    # one of these names later owns it and this line decides nothing.
    FAMILY_OF.setdefault(_screen, FAMILY_3)

_re = _contract.re
# A policy states its write in verbs `WRITE_RE` does not carry: the manifest
# policy four units carried spelled it `regenerates`, so no family read it.
POLICY_WRITE_RE = _re.compile(
    r"\b(?:write|writes|create|creates|emit|emits|append|appends|record|records"
    r"|regenerate|regenerates|rewrite|rewrites|update|updates)\b", _re.IGNORECASE)
# Whose write it is. A Fixed inputs section states the run's law, and most of
# that law is somebody else's act -- the join appends the covered line, the
# integrator regenerates the manifest. Read as this item's, those sentences
# report every unit of a run for a write none of them makes.
OTHER_ACTOR_RE = _re.compile(
    r"\b(?:join|integrator|gate|engine|decomposer|frontier|checker|orchestrator"
    r"|reviewer|caller|host)\s+(?:\w+\s+){0,2}$", _re.IGNORECASE)
# `DENIAL_RE` with one noun allowed through: a policy denies in the plural --
# "no unit appends to the sink's covered.jsonl".
POLICY_DENIAL_RE = _re.compile(
    r"\b(?:not|never|no|without|rather than)\s+(?:\w+\s+)?$", _re.IGNORECASE)
ACTOR_WINDOW = 48
DELETION_RE = _re.compile(
    r"\b(?:delete|deletes|deleting|deleted|remove|removes|removing|removed"
    r"|drop|drops|dropping|dropped|strike|strikes|striking)\b", _re.IGNORECASE)
RELOCATION_RE = _re.compile(
    r"\b(?:move|moves|moving|moved|relocate|relocates|relocating|relocated"
    r"|rename|renames|renaming|renamed)\b", _re.IGNORECASE)
# The argument evidence has to stand behind, and the evidence that stands
# behind it. One plan called the live read path unreachable and was believed.
REACHABILITY_RE = _re.compile(
    r"\b(?:unreachable|unreached|never reached|nothing reaches|no callers?"
    r"|no consumers?|dead code)\b", _re.IGNORECASE)
PROBE_RE = _re.compile(
    r"\b(?:probe|probes|probed|ablation|census|reachability)\b", _re.IGNORECASE)


def _policy_scope(frontmatter, inputs):
    """Screen 1: a fixed-input policy ordering a write outside the grant.

    Attribution is the whole difficulty: this reads a wider verb set than
    family 3's other half and a narrower subject, because only a policy
    sentence naming this item commits it.
    """

    scope = _scope._listed(frontmatter, "write_scope")
    flat = _scope._flat(inputs)
    findings, seen = [], set()
    for match in POLICY_WRITE_RE.finditer(flat):
        if _contract.SCOPE_WORD_RE.match(flat[match.end():]):
            continue
        before = flat[max(0, match.start() - ACTOR_WINDOW):match.start()]
        if POLICY_DENIAL_RE.search(before) or OTHER_ACTOR_RE.search(before):
            continue
        end = match.end() + _contract.WRITE_WINDOW
        window = flat[match.end():end]
        if len(flat) > end and not flat[end].isspace():
            window = window.rpartition(" ")[0]
        for target in _scope._paths_in(window.partition(";")[0]):
            if target in seen or _scope._covered(target, scope):
                continue
            seen.add(target)
            findings.append((POLICY_OUTSIDE_SCOPE, target))
    return findings


def _deleted_phrases(objective):
    """Every multi-word span this objective says it deletes.

    A phrase, not a literal: `_literals` reads the single token a removal
    names, and cannot see a sentence of prose taken out of a document -- which
    is what a test asserts word for word.
    """

    flat = _scope._flat(objective)
    found = []
    for match in DELETION_RE.finditer(flat):
        before = flat[max(0, match.start() - _contract.DENIAL_WINDOW):match.start()]
        if _contract.DENIAL_RE.search(before):
            continue
        window = flat[match.end():match.end() + _contract.REMOVAL_WINDOW]
        for quote in _contract.QUOTE_RE.finditer(window):
            phrase = _scope._flat(quote.group(1) or quote.group(2) or "")
            if " " in phrase and phrase not in found:
                found.append(phrase)
    return found


def _consumer_census(frontmatter, objective, tree):
    """Screen 2: the checks asserting a phrase this item is ordered to delete.

    Over ``tests/`` alone, because that is where a pin is a failing check
    rather than a mention -- which is also why this refuses where the reverse
    scan beside it is advisory.
    """

    phrases = _deleted_phrases(objective)
    if not phrases or tree is None:
        return []
    scope = _scope._listed(frontmatter, "write_scope")
    findings = []
    for rel, text in _scope._pin_index(tree):
        if not rel.startswith("tests/") or _scope._covered(rel, scope):
            continue
        hits = [phrase for phrase in phrases if phrase in text]
        if hits:
            findings.append(
                (UNGRANTED_CONSUMER, '{} asserts "{}"'.format(rel, max(hits, key=len))))
    return findings


def _removal_evidence(frontmatter, objective, inputs):
    """Screen 3: a removal argued from reachability with no probe behind it.

    Graded on the argument rather than on the deletion, so a cut that removes
    a directory and claims nothing about who reaches it is asked for nothing;
    and on the Fixed inputs rather than the Completion test, because a
    criterion promising a new test will prove unreachability is the claim
    again with a date on it, not evidence the cut was made from.
    """

    claim = REACHABILITY_RE.search(_scope._flat(objective))
    if claim is None or PROBE_RE.search(_scope._flat(inputs)):
        return []
    return [(UNPROBED_REMOVAL, "reachability claimed at {!r}, no probe among the "
             "fixed inputs".format(claim.group(0)))]


def _marker_only_relocation(objective, completion):
    """Screen 4: a relocation whose completion test is substring markers alone.

    Advisory by class: a marker is weak evidence of meaning, never proof of
    its absence.
    """

    if not RELOCATION_RE.search(_scope._flat(objective)):
        return False
    heads = [
        span.strip().split()[0]
        for span in _contract.BACKTICK_RE.findall(completion)
        if span.strip().split()[:1]
    ]
    return bool(heads) and all(head in _contract.SEARCH_HEADS for head in heads)


GATE_VERIFY_SUFFIX = '.gate.verify'


def _frozen_authority(ticket_id, is_root):
    """Is this item's write authority its frontmatter's alone?

    A root freezes the cumulative acceptance its units deliver, and its
    ``gate.verify`` stub re-runs that same acceptance.  Neither writes what
    those criteria describe -- the units do -- so a criterion such as
    "records required-check-run/v1" names a unit's artifact and commits the
    frozen item to nothing.  Their own Objective and frontmatter authority
    stay graded, and a unit's Completion test still commits the unit.
    """
    return is_root or ticket_id.endswith(GATE_VERIFY_SUFFIX)

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
    # A top-level root freezes acceptance; commands in that acceptance observe
    # the unit result and can therefore name paths absent from the baseline.
    # That positional exemption covers only command-argument path existence;
    # write-looking Completion-test prose is `_frozen_authority`'s, which
    # reads the root and its gate.verify stub alike.  Command shape,
    # citations, and each item's own Objective/frontmatter authority remain
    # graded.  A nested decomposer is not a root and receives no exemption.
    is_root = ticket_id in _root_ids(siblings)
    # Resolved once for the item: the same section answers every criterion, and
    # a frozen item's completion test is the acceptance itself, so naming the
    # gate's row there is what it is for rather than a defect of it.
    frozen = _frozen_authority(ticket_id, is_root)
    literals = {} if frozen else _input_literals(sections.get(INPUTS_SECTION, ""))
    for number, criterion in _criteria(sections.get(COMPLETION_SECTION, "")):
        prose = _prose(criterion)
        findings.extend(
            (ticket_id, number, klass, detail)
            for klass, detail in _path_reality(prose, baseline_tree)
        )
        commands = _commands(criterion)
        # An oracle naming the fixed input that holds its command states that
        # command through a name. Read before the gap below, because the gap
        # says no extractor recognized the oracle and this one recognized it.
        indirect = _indirect_whole_suite(criterion, literals, baseline_tree)
        if indirect is not None:
            findings.append(
                (ticket_id, number, WHOLE_SUITE_ORACLE, "{}: {}".format(*indirect))
            )
        if not commands:
            if indirect is not None:
                continue
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
            if missing and not is_root:
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
    completion = sections.get(COMPLETION_SECTION, "")
    if frozen:
        completion = ""
    body = "\n".join((sections.get(OBJECTIVE_SECTION, ""), completion))
    findings.extend(
        (ticket_id, 0, klass, detail)
        for klass, detail in _scope_closure(frontmatter, _prose(body))
    )
    objective = _prose(sections.get(OBJECTIVE_SECTION, ""))
    findings.extend(
        (ticket_id, 0, klass, detail)
        for klass, detail in _scope_open(frontmatter, objective, baseline_tree)
    )
    inputs = sections.get(INPUTS_SECTION, "")
    if not frozen:
        # `_frozen_authority`'s exemption, for the same reason it exists: a
        # root's Fixed inputs state the run's law, and the root writes none of
        # what that law describes.
        findings.extend(
            (ticket_id, 0, klass, detail)
            for klass, detail in _policy_scope(frontmatter, _prose(inputs))
        )
    findings.extend(
        (ticket_id, 0, klass, detail)
        for klass, detail in _consumer_census(frontmatter, objective, baseline_tree)
    )
    # Evidence, not authority, so no frozen item is exempt: a root arguing
    # unreachability without a probe is the same defect at its source.
    findings.extend(
        (ticket_id, 0, klass, detail)
        for klass, detail in _removal_evidence(frontmatter, objective, inputs)
    )
    # Family 3's pricing and root-admissibility screens. No frozen exemption:
    # every one of them reads this item's own grant, mutation plan or pack
    # stamp, which is the authority `_frozen_authority` leaves graded -- and a
    # root is the only item the last two can be asked about at all.
    findings.extend(
        (ticket_id, 0, klass, detail)
        for klass, detail in _pricing.screens(
            frontmatter, objective, inputs, baseline_tree, is_root)
    )
    # Screen 4, and advisory rather than refusing: a marker is weak evidence of
    # meaning, never proof of its absence. Read off the section rather than the
    # `completion` local above, which a frozen root blanks -- the question here
    # is what the completion test spells, not whose law it states.
    if _marker_only_relocation(objective, sections.get(COMPLETION_SECTION, "")):
        findings.append((ticket_id, 0, MARKER_ONLY_RELOCATION,
                         "relocation graded by substring markers alone"))
    return findings


# What the caller reads off the status, and what the status does not mean. The
# six families are the module docstring's to describe; this names none of them.

__all__ = (
    '_check_ticket', '_policy_findings', '_frozen_authority',
    '_policy_scope', '_deleted_phrases', '_consumer_census',
    '_removal_evidence', '_marker_only_relocation',
    'POLICY_OUTSIDE_SCOPE', 'UNGRANTED_CONSUMER', 'UNPROBED_REMOVAL',
    'MARKER_ONLY_RELOCATION', 'UNPRICED_GROWTH', 'UNSPLITTABLE_OWNER',
    'CEILING_WITHOUT_ARITHMETIC', 'UNPINNED_OUTPUT',
    'PACK_INADMISSIBLE_ROOT', 'EXCLUDED_REQUIRED_COMMAND',
)
