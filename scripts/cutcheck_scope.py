"""Grade citations, paths, and write-scope closure."""

try:  # repository checkout
    from scripts import cutcheck_contract as _contract
except ImportError:  # installed flat script directory
    import cutcheck_contract as _contract
BACKTICK_RE = _contract.BACKTICK_RE
CITATION_RE = _contract.CITATION_RE
CITED_LINES = _contract.CITED_LINES
COMMAND_HEADS = _contract.COMMAND_HEADS
DENIAL_RE = _contract.DENIAL_RE
DENIAL_WINDOW = _contract.DENIAL_WINDOW
DOTTED_RE = _contract.DOTTED_RE
GLOB_RE = _contract.GLOB_RE
LITERAL_MARKS = _contract.LITERAL_MARKS
LITERAL_RE = _contract.LITERAL_RE
PIN_ROOTS = _contract.PIN_ROOTS
PIN_SIZE_LIMIT = _contract.PIN_SIZE_LIMIT
PLACEHOLDER_RE = _contract.PLACEHOLDER_RE
QUOTE_NOT_AT_CITATION = _contract.QUOTE_NOT_AT_CITATION
QUOTE_RE = _contract.QUOTE_RE
QUOTE_WINDOW = _contract.QUOTE_WINDOW
REMOVAL_RE = _contract.REMOVAL_RE
REMOVAL_WINDOW = _contract.REMOVAL_WINDOW
SCOPE_CONTRADICTION = _contract.SCOPE_CONTRADICTION
SCOPE_OPEN = _contract.SCOPE_OPEN
SCOPE_WORD_RE = _contract.SCOPE_WORD_RE
SECTION_CITATION_RE = _contract.SECTION_CITATION_RE
UNRESOLVED_CITATION = _contract.UNRESOLVED_CITATION
UNSCOPED_WRITE = _contract.UNSCOPED_WRITE
WRITE_RE = _contract.WRITE_RE
WRITE_WINDOW = _contract.WRITE_WINDOW
_PIN_INDEX = _contract._PIN_INDEX
_PIN_SKIPPED = _contract._PIN_SKIPPED
re = _contract.re

try:  # repository checkout
    from scripts import cutcheck_state as _state
except ImportError:  # installed flat script directory
    import cutcheck_state as _state
_unread = _state._unread

try:  # repository checkout
    from scripts import tickets_scope as _tickets_scope
except ImportError:  # installed flat script directory
    import tickets_scope as _tickets_scope

def _flat(text):
    return " ".join(text.split())


def _prose(text):
    """Ticket text with its oracle commands removed: claims, not commands.

    A pattern inside a command is that command's argument, never a quotation
    and never a path the item names.
    """

    return BACKTICK_RE.sub(
        lambda m: " " if m.group(1).strip().split(" ", 1)[0] in COMMAND_HEADS else m.group(0),
        text,
    )


def _listed(frontmatter, key):
    """A frontmatter field written either as a scalar or as a list."""

    value = frontmatter.get(key) or []
    if isinstance(value, str):
        value = [value]
    return [str(item).strip() for item in value if str(item).strip()]


def _granted(frontmatter, siblings):
    """This item's write scope, plus every ``depends_on`` ancestor's.

    An item's oracles run at the item's revision, which contains the work of
    every ancestor it depends on, so a path an ancestor creates is present.
    """

    scopes = _listed(frontmatter, "write_scope")
    pending = _listed(frontmatter, "depends_on")
    seen = set()
    while pending:
        ancestor = pending.pop()
        if ancestor in seen or ancestor not in siblings:
            continue
        seen.add(ancestor)
        scopes.extend(_listed(siblings[ancestor], "write_scope"))
        pending.extend(_listed(siblings[ancestor], "depends_on"))
    return scopes


def _covered(rel, scopes):
    """Is ``rel`` inside one of ``scopes``?

    Containment runs one way: a grant covers itself and what is under it, never
    the directory that holds it -- a grant of one file is no licence over its
    parent. A bare filename names no directory, so the one grant that provably
    holds it is the grant whose own basename it is; a granted directory that
    happens to be somewhere it could live covers nothing.
    """

    target = rel.strip().strip("/")
    for entry in scopes:
        scope = entry.strip().strip("/")
        if not scope:
            continue
        if _tickets_scope.path_covers(scope, target):
            return True
        if "/" not in target and scope.rsplit("/", 1)[-1] == target:
            return True
    return False


def _overlaps(left, right):
    return _tickets_scope.path_covers(left, right) or _tickets_scope.path_covers(right, left)


def _path_args(command):
    """Unquoted argv tokens naming a path: an argument, a redirect target.

    A quoted token is a pattern or a literal the oracle carries, not a path it
    reaches for. Absolute and interpolated paths lie outside the scratch copy,
    so they are nothing this tool can resolve.
    """

    found = []
    for token in command.split()[1:]:
        if token[:1] in ("-", '"', "'"):
            continue
        token = token.lstrip(">").split("::", 1)[0].rstrip(",;")
        if not token or token[:1] in ("/", "~", "$") or GLOB_RE.search(token):
            continue
        if "/" in token or DOTTED_RE.search(token):
            found.append(token)
    return found


def _paths_in(text):
    """Tokens in prose that name a path: a slash, or a short final extension.

    A token holding an angle bracket is a placeholder for wherever the run puts
    its state, so no item's grant can name it and its absence is no defect.
    """

    found = []
    for token in text.replace("`", " ").split():
        token = token.lstrip("(<[\"'").rstrip(")>],;:.\"'")
        if not token or token[:1] == "-" or GLOB_RE.search(token):
            continue
        if PLACEHOLDER_RE.search(token):
            continue
        if "/" in token or DOTTED_RE.search(token):
            found.append(token)
    return found


def _where(rel, line, section):
    return "{}:{}".format(rel, line) if line else "{} §{}".format(rel, section)


def _cited_text(tree, rel, line, section):
    """The text a citation points at, or None when the citation misses.

    Resolution is at the baseline scratch copy, never at the workspace: a
    ticket cites the tree it was cut from, which the work then changes.
    """

    path = tree / rel
    if not path.is_file():
        return None
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    if line is not None:
        if line > len(lines):
            return None
        return _flat(" ".join(lines[max(0, line - 1 - CITED_LINES):line + CITED_LINES]))
    opens = re.compile(r"^#*\s*{}\.\s".format(section))
    following = re.compile(r"^#*\s*\d+\.\s")
    start = None
    for index, text in enumerate(lines):
        if start is None:
            if opens.match(text):
                start = index
        elif following.match(text):
            return _flat(" ".join(lines[start:index]))
    return None if start is None else _flat(" ".join(lines[start:]))


def _citations(prose):
    """Every ``file:line`` and ``file §N`` location a ticket points at."""

    found = [
        (m.start(), m.group(1), int(m.group(2)), None)
        for m in CITATION_RE.finditer(prose)
    ]
    found += [
        (m.start(), m.group(1), None, int(m.group(2)))
        for m in SECTION_CITATION_RE.finditer(prose)
    ]
    return [c for c in found if not c[1].startswith(("/", "~")) and ".." not in c[1]]


def _path_reality(prose, baseline_tree):
    """Family 2 over prose: citations resolve, and a quote is where it is cited.

    A quotation is multi-word text in quotes or in backticks -- a single token
    beside a citation names something, it does not quote it. Backticks count
    because a quoted line of code carries quotes of its own. A span holding a
    citation is that citation with what it points at, never a quotation of the
    line: the ticket is saying where, not what.
    """

    findings = []
    cites = _citations(prose)
    for _, rel, line, section in cites:
        if _cited_text(baseline_tree, rel, line, section) is None:
            findings.append((UNRESOLVED_CITATION, _where(rel, line, section)))
    for match in QUOTE_RE.finditer(prose):
        quoted = _flat(match.group(1) or match.group(2) or "")
        near = [c for c in cites if abs(c[0] - match.start()) <= QUOTE_WINDOW]
        if " " not in quoted or not near or _citations(quoted):
            continue
        _, rel, line, section = min(near, key=lambda c: abs(c[0] - match.start()))
        text = _cited_text(baseline_tree, rel, line, section)
        if text is None or quoted in text:
            continue
        findings.append(
            (
                QUOTE_NOT_AT_CITATION,
                '"{}" not at {}'.format(quoted, _where(rel, line, section)),
            )
        )
    return findings


def _scope_closure(frontmatter, prose):
    """Family 3: the grant covers every write, and contradicts no exclusion.

    Observing is not naming: a path the item only reads stays outside its write
    scope and is no defect here, and neither is one the text mentions without
    committing to write. "Write scope" is the grant's name rather than a write,
    and a denied write -- never written, not created -- commits the item to
    nothing at all.
    """

    scope = _listed(frontmatter, "write_scope")
    findings = []
    seen = set()
    flat = _flat(prose)
    for match in WRITE_RE.finditer(flat):
        if SCOPE_WORD_RE.match(flat[match.end():]):
            continue
        if DENIAL_RE.search(flat[max(0, match.start() - DENIAL_WINDOW):match.start()]):
            continue
        end = match.end() + WRITE_WINDOW
        window = flat[match.end():end]
        if len(flat) > end and not flat[end].isspace():
            window = window.rpartition(" ")[0]
        for target in _paths_in(window):
            if target in seen or _covered(target, scope):
                continue
            seen.add(target)
            findings.append((UNSCOPED_WRITE, target))
    for action in _listed(frontmatter, "excluded_actions"):
        for target in _paths_in(action):
            for entry in scope:
                if _overlaps(target, entry):
                    findings.append((SCOPE_CONTRADICTION, "{} | {}".format(action, entry)))
                    break
    return findings


def _is_literal(token):
    """Is this token specific enough that a file pinning it means something?

    Three characters and a separator. `gate`, `set` and `the` are words every
    tree is full of; `orch-compose`, `SCRIPT_NAMES` and `scripts/tickets.py`
    are things one file states and another depends on.
    """

    return bool(LITERAL_RE.match(token)) and any(m in token for m in LITERAL_MARKS)


def _literals(objective):
    """Every literal this objective says it deletes, moves or renames.

    The window and the denial frame are ``_scope_closure``'s, asked of a verb
    that takes away rather than one that adds: a write the ticket denies
    commits it to nothing, and neither does a removal it denies.

    A path is read twice -- whole, and as the name it ends in. The pin is
    usually on the name: ``scripts/tickets.py`` spells a deleted engine as a
    set member and nothing outside the library spells the directory it lived
    in, so reading the path alone finds no pin and reports the cut clean.
    """

    flat = _flat(objective)
    found = []
    for match in REMOVAL_RE.finditer(flat):
        if DENIAL_RE.search(flat[max(0, match.start() - DENIAL_WINDOW):match.start()]):
            continue
        end = match.end() + REMOVAL_WINDOW
        window = flat[match.end():end]
        if len(flat) > end and not flat[end].isspace():
            window = window.rpartition(" ")[0]
        # A span the objective itself sets in backticks is a literal on the
        # author's word, separator or none: `limited`, `checker`, `gate` are
        # enum and set members a cut removes, and the tree's ordinary uses of
        # the same word are told apart at the pin by ``_pins``' boundaries.
        spans = [(t, False) for t in _paths_in(window)]
        spans += [(s.strip(), True) for s in BACKTICK_RE.findall(window)]
        for token, marked in spans:
            for candidate in (token, token.rsplit("/", 1)[-1]):
                literal = _is_literal(candidate) or (
                    marked and bool(LITERAL_RE.match(candidate))
                )
                if literal and candidate not in found:
                    found.append(candidate)
    return found


def _pins(literal, text):
    """Does ``text`` state ``literal`` as a name, not as the inside of one?

    Whole-token: `orch-compose` is not pinned by `orch-composer`, `gate` not
    by `delegate`, `friction.py` not by `friction.pyc`. A path separator, a
    dot, a quote or a bracket on either side is a boundary; a word character
    or a dash is not.
    """

    return re.search(r"(?<![\w-])" + re.escape(literal) + r"(?![\w-])", text) is not None


def _pin_index(tree):
    """Every file under ``PIN_ROOTS`` of this tree, with its text, read once.

    Read from the baseline copy, where every other file-reading family reads:
    a pin is a fact about the tree the ticket was cut from, which the work then
    changes. Built lazily and cached per tree, because the only cut that pays
    for it is one whose objective takes a literal away.
    """

    key = str(tree)
    if key in _PIN_INDEX:
        # Replayed, not skipped: the index is cached per tree and outlives the
        # invocation that built it, so a second run reading the same copy would
        # otherwise be handed a shorter index than the first and told nothing
        # about the difference.
        for what in _PIN_SKIPPED.get(key, ()):
            _unread(what)
        return _PIN_INDEX[key]
    skipped = []
    entries = []
    for root in PIN_ROOTS:
        base = tree / root
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            try:
                if not path.is_file():
                    continue
                if path.stat().st_size > PIN_SIZE_LIMIT:
                    # Skipped and said: the index holding no pin from this
                    # file is a fact about the reading, and read as a fact
                    # about the file it licenses a grant the file breaks.
                    skipped.append("{}: past PIN_SIZE_LIMIT, not read for pins".format(
                        path.relative_to(tree).as_posix()))
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError as error:
                skipped.append("{}: not read for pins: {}".format(
                    path.relative_to(tree).as_posix(), error))
                continue
            entries.append((path.relative_to(tree).as_posix(), text))
    for what in skipped:
        _unread(what)
    _PIN_INDEX[key] = entries
    _PIN_SKIPPED[key] = skipped
    return entries


def _scope_open(frontmatter, objective, tree):
    """Advisory reverse scan for an exact reference outside the grant.

    A reference can suggest an undeclared structural edge, but never proves
    causality, widens authority, or changes the exit status.  One advisory per
    pinning file names the most specific literal it holds.
    """

    literals = _literals(objective)
    if not literals or tree is None:
        return []
    scope = _listed(frontmatter, "write_scope")
    findings = []
    for rel, text in _pin_index(tree):
        if _covered(rel, scope):
            continue
        pinning = [
            literal
            for literal in literals
            if _pins(literal, text) and not _covered(rel, [literal])
        ]
        if pinning:
            findings.append(
                (SCOPE_OPEN, "{} pins {}".format(rel, max(pinning, key=len)))
            )
    return findings

__all__ = (
    '_flat', '_prose', '_listed', '_granted',
    '_covered', '_overlaps', '_path_args', '_paths_in',
    '_where', '_cited_text', '_citations', '_path_reality',
    '_scope_closure', '_is_literal', '_literals', '_pins',
    '_pin_index', '_scope_open',
)
