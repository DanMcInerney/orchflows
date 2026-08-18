"""Extract and classify cutcheck oracle commands."""

try:  # repository checkout
    from scripts import cutcheck_contract as _contract
except ImportError:  # installed flat script directory
    import cutcheck_contract as _contract
BACKTICK_RE = _contract.BACKTICK_RE
COMMAND_HEADS = _contract.COMMAND_HEADS
CUMULATIVE_RANGE = _contract.CUMULATIVE_RANGE
CUMULATIVE_RE = _contract.CUMULATIVE_RE
DENIAL_RE = _contract.DENIAL_RE
DENIAL_WINDOW = _contract.DENIAL_WINDOW
EVAL_ARGS = _contract.EVAL_ARGS
EVAL_HEADS = _contract.EVAL_HEADS
GIT_CONFINED_SUBCOMMANDS = _contract.GIT_CONFINED_SUBCOMMANDS
GIT_HEAD = _contract.GIT_HEAD
MENTION_RE = _contract.MENTION_RE
ORACLE_CLASS_RE = _contract.ORACLE_CLASS_RE
PROVENANCE_RE = _contract.PROVENANCE_RE
STAMP_CONTINUES_RE = _contract.STAMP_CONTINUES_RE
STAMP_OPENS_RE = _contract.STAMP_OPENS_RE
SWALLOWED_EXIT = _contract.SWALLOWED_EXIT
SWALLOW_RE = _contract.SWALLOW_RE
UNCONFINED_ORACLE = _contract.UNCONFINED_ORACLE
_ticket_criteria = _contract._ticket_criteria
shlex = _contract.shlex

def _criteria(section):
    """Every completion-test criterion, numbered as the ticket's own grader
    numbers them.

    Parsing is ``scripts/tickets.py``'s. That script refuses a criterion this
    tool then grades, so two parsers here is exactly how a section reads one
    way to the cut's refusal and another way to the cut's check: a bullet
    criterion was invisible to this tool while being graded there. The
    numbering is positional for the same reason -- ``criterion_defects`` says
    "criterion 2" about the second criterion in the section, whatever digit
    the author typed, and a report naming a different number names a
    criterion its reader cannot find.
    """

    return list(enumerate(_ticket_criteria(section), start=1))


def _oracle_class(criterion):
    """The class this criterion states its oracle is decided by, or ``""``."""

    match = ORACLE_CLASS_RE.search(criterion)
    return match.group(1).strip().lower() if match else ""


def _stated_provenance(criterion):
    """The provenance this criterion stamps of its own oracle, or ``""``.

    A stamp, never a mention: the field is read with ``tickets.PROVENANCE_RE``
    and kept only where the frame around it is a statement -- opened by the
    start of the criterion, a sentence boundary or the field separator
    ``tickets.py`` itself writes, and continued by no word.
    """

    for match in PROVENANCE_RE.finditer(criterion):
        if not STAMP_OPENS_RE.search(criterion[:match.start()]):
            continue
        if STAMP_CONTINUES_RE.match(criterion[match.end():]):
            continue
        return match.group(1).strip().lower()
    return ""


def _unreadable_search(command):
    """Defer the search-shape question until the search module is loaded."""
    try:
        from scripts.cutcheck_search import _unreadable_search as unreadable
    except ImportError:  # installed flat script directory
        from cutcheck_search import _unreadable_search as unreadable
    return unreadable(command)


def _commands(criterion):
    """Backtick spans stating a command: a known head, carrying an argument.

    A head with nothing after it is the tool's name, and no bare name is a
    decidable cut oracle. ``git`` alone prints its usage and ``grep`` alone
    errors, whichever revision reads them. ``pytest`` alone does run something,
    but a whole-suite invocation naming no node id reads the same under every
    item it is stated under, so it discriminates none of them -- a cut defect
    either way, and the honest report of it is the gap.

    Stating is not quoting, and the frame standing immediately in front of the
    span is what tells them apart -- ``_scope_closure``'s question about a
    write verb, asked again of a command. Grading a quotation reaches for a
    path the item never claimed, refuses the very span a ticket was describing,
    and runs whatever the prose says something else runs.
    """

    found = []
    for match in BACKTICK_RE.finditer(criterion):
        candidate = match.group(1).strip()
        argv = candidate.split()
        if len(argv) < 2 or argv[0] not in COMMAND_HEADS or _evaluates_code(argv):
            continue
        if _unreadable_search(candidate):
            continue
        frame = criterion[max(0, match.start() - DENIAL_WINDOW):match.start()]
        if DENIAL_RE.search(frame) or MENTION_RE.search(frame):
            continue
        found.append(candidate)
    return found


def _evaluates_code(argv):
    """Does this span hand an interpreter a program to evaluate?

    ``python3 -c '<anything>'`` is ``bash -lc '<anything>'`` through a head an
    extractor accepts: the argument is the program, and ticket content is
    untrusted. A bare ``-`` is the same span with the program left on stdin.
    """

    return argv[0] in EVAL_HEADS and any(token in EVAL_ARGS for token in argv[1:])


def _names_outside_the_copy(token):
    """Does this argv token spell a location the scratch copy does not hold?

    Two spellings, and this catches both: root the path, or climb out of it.
    Nothing expands on the way -- argv is split, never evaluated, and git spawns
    no shell, so ``~`` and ``$HOME`` name a directory inside the copy and
    nothing else.

    Not closed by construction, because a third route exists that argv cannot
    see: name a symlink the copy holds. Measured -- commit a symlink, run ``git
    diff --output=link/x``, and the file lands outside the copy while this
    returns False. That hole and the permitted span that writes *inside* the
    copy are one problem said twice: text cannot answer a containment question,
    because where a path lands is a fact about the tree and not about the token.
    The copy has to enforce confinement. A rule that only describes it will keep
    coming up one route short, so this narrows the reachable set without closing
    it.

    An option's value starts where the option stops -- after ``=`` for a long
    one, after the letter for a short one carrying its value attached -- and an
    operand is its own value. ``..`` counts only as a whole path component, so
    ``<base>..HEAD`` stays the revision range it is.
    """

    if token.startswith("--"):
        _, _, value = token.partition("=")
    elif token.startswith("-"):
        value = token[2:]
    else:
        value = token
    return value.startswith("/") or ".." in value.split("/")


def _unconfined_git(command):
    """Is this a git span the scratch copy does not confine?

    Two questions, because an escape takes two shapes and one test sees one of
    them. Position answers the first: every way git runs a program named on the
    line or leaves the tree it was pointed at is a global option, and a global
    option is exactly a token standing before the subcommand, so a confined set
    holding no token that begins with ``-`` refuses that family entire.

    Position cannot answer the second, and a subcommand check alone is narrower
    than the threat. ``--output=<file>`` is a subcommand option: it stands after
    the subcommand, where the position rule cannot see it, and ``git diff``,
    ``git log``, ``git show`` and ``git rev-list`` each take it and write the
    file, absolute or climbing, inside the copy or beside it. ``-O<orderfile>``,
    ``--exclude-from`` and ``--no-index`` read the same way round. So the second
    question is asked of what a token spells rather than where it stands, and
    ``_names_outside_the_copy`` answers it for every option git ships next --
    as far as text can, which is not all the way; see its own docstring.

    What remains -- a pager, an alias, a textconv or ext-diff driver -- git
    takes from configuration, and configuration is the clone's own: ``git
    clone`` writes a fresh ``core``-only config, an in-tree ``.gitattributes``
    can name a driver but cannot define one, and a ticket supplies argv and
    nothing besides.

    Tokenised the way ``_run_once`` tokenises, so the span read here is the argv
    that would run: a gate splitting the text some other way grades one command
    and executes another.
    """

    try:
        argv = shlex.split(command)
    except ValueError:
        return False
    if not argv or argv[0] != GIT_HEAD:
        return False
    if len(argv) < 2 or argv[1] not in GIT_CONFINED_SUBCOMMANDS:
        return True
    return any(_names_outside_the_copy(token) for token in argv[2:])


def _shape(command):
    """The defects the command text carries, judged without running it."""

    classes = []
    if SWALLOW_RE.search(command):
        classes.append(SWALLOWED_EXIT)
    if CUMULATIVE_RE.search(command):
        classes.append(CUMULATIVE_RANGE)
    if _unconfined_git(command):
        classes.append(UNCONFINED_ORACLE)
    return classes

__all__ = (
    '_criteria', '_oracle_class', '_stated_provenance', '_commands',
    '_evaluates_code', '_names_outside_the_copy', '_unconfined_git', '_shape',
)
