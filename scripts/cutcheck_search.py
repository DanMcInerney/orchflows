"""Evaluate search spans and whole-suite command shape."""

try:  # repository checkout
    from scripts import cutcheck_contract as _contract
    from scripts import tickets_format as _syntax
except ImportError:  # installed flat script directory
    import cutcheck_contract as _contract
    import tickets_format as _syntax
COUNT_FLAG_RE = _contract.COUNT_FLAG_RE
GIT_COUNT_FLAG = _contract.GIT_COUNT_FLAG
GIT_HEAD = _contract.GIT_HEAD
NO_MATCH = _contract.NO_MATCH
Path = _contract.Path
SEARCH_ERROR = _contract.SEARCH_ERROR
SEARCH_FLAGS = _contract.SEARCH_FLAGS
SEARCH_HEADS = _contract.SEARCH_HEADS
SEARCH_LONG_FLAGS = _contract.SEARCH_LONG_FLAGS
SEARCH_PATTERN_FLAG = _contract.SEARCH_PATTERN_FLAG
os = _contract.os
re = _contract.re
shlex = _contract.shlex
# The oracle-shape vocabulary and the whole-suite detector belong to the
# syntax owner, `scripts/tickets_format.py`: a criterion's oracle is ticket
# syntax, and `tickets.py lint` grades it without cutcheck in the room.
# Read here rather than restated, so one reading decides both callers.
DISCOVER = _syntax.DISCOVER
FILTER_MATCHES_ALL = _syntax.FILTER_MATCHES_ALL
NODE_FILTER = _syntax.NODE_FILTER
NODE_SEP = _syntax.NODE_SEP
TEST_RUNNERS = _syntax.TEST_RUNNERS
_filter_narrows = _syntax._filter_narrows
_whole_suite = _syntax._whole_suite
_whole_target = _syntax._whole_target

def _search_span(argv):
    """A search span as ``(letters, pattern, operands)``, or None where a token
    outside the closed option set stands in it.

    Short options cluster, a long one may carry its value after ``=``, ``--``
    ends the options, and the pattern is ``-e``'s value where one is given and
    the first operand otherwise. Two patterns are two searches ORed together in
    a syntax the pattern itself may not be written in, so a span naming more
    than one is a span this declines to read rather than one it guesses at.
    """

    letters = set()
    patterns = []
    words = []
    rest = list(argv[1:])
    ended = False
    while rest:
        token = rest.pop(0)
        if ended or not token.startswith("-") or token == "-":
            words.append(token)
            continue
        if token == "--":
            ended = True
            continue
        if token.startswith("--"):
            name, sep, value = token[2:].partition("=")
            letter = SEARCH_LONG_FLAGS.get(name)
            if letter is None:
                return None
            if letter == SEARCH_PATTERN_FLAG:
                if not sep:
                    if not rest:
                        return None
                    value = rest.pop(0)
                patterns.append(value)
            elif sep:
                return None
            else:
                letters.add(letter)
            continue
        cluster = token[1:]
        while cluster:
            letter, cluster = cluster[0], cluster[1:]
            if letter == SEARCH_PATTERN_FLAG:
                if not cluster:
                    if not rest:
                        return None
                    cluster = rest.pop(0)
                patterns.append(cluster)
                cluster = ""
            elif letter in SEARCH_FLAGS:
                letters.add(letter)
            else:
                return None
    if len(patterns) > 1:
        return None
    if patterns:
        return letters, patterns[0], words
    if not words:
        return None
    return letters, words[0], words[1:]


def _search_matcher(letters, pattern):
    """The compiled matcher for one search span, or None where the pattern is
    one nothing here compiles -- which is a status the search heads have too.

    Bytes, because a search reads whatever the tree holds and a tree holds
    files no encoding decodes. ``-F`` reads the pattern literally and every
    other spelling reads it as a regular expression, which agrees with the
    extended syntax ``-E`` names on every pattern this repository's ticket
    corpus states.
    """

    body = re.escape(pattern) if "F" in letters else pattern
    if "w" in letters:
        # grep's ``-w`` asks that no word constituent stand on either side of
        # the match, which is not ``\b``: ``\b`` also demands one *inside*, so
        # a pattern whose own edge is not a word character -- ``-w -- -x`` --
        # would never match here and does under grep.
        body = r"(?<!\w)(?:{})(?!\w)".format(body)
    if "x" in letters:
        body = r"\A(?:{})\Z".format(body)
    try:
        return re.compile(
            body.encode("utf-8", "surrogateescape"),
            re.IGNORECASE if "i" in letters else 0,
        )
    except re.error:
        return None


def _selected(matcher, path, inverted):
    """Does this file hold a selected line? None where it could not be read."""

    try:
        data = path.read_bytes()
    except OSError:
        return None
    lines = data.split(b"\n")
    if lines and not lines[-1]:
        lines.pop()
    return any(bool(matcher.search(line)) != inverted for line in lines)


def _files_under(directory):
    """Every regular file the copy holds beneath this directory.

    ``followlinks=False``, and symlinked files are skipped: a link the copy
    holds is the one route out of it that a path cannot be read for, which
    ``_names_outside_the_copy`` says at length about the git spans. Answering
    the search heads here is what makes it closable, so it is closed.
    """

    for base, dirs, names in os.walk(str(directory), followlinks=False):
        dirs.sort()
        for name in sorted(names):
            path = Path(base) / name
            if not path.is_symlink():
                yield path


def _inside_the_copy(tree, operand):
    """The path this operand names inside the tree, or None where it names one
    outside it."""

    here = Path(tree) / operand
    try:
        root = Path(tree).resolve()
        resolved = here.resolve()
    except OSError:
        return None
    if resolved != root and root not in resolved.parents:
        return None
    return here


def _search_exit(argv, tree):
    """The status a search span exits with, decided by this tool's own matcher.

    The convention ``grep`` and ``rg`` share: 0 where a line was selected,
    ``NO_MATCH`` where none was, and ``SEARCH_ERROR`` where the span named
    something this could not read. ``_discrimination`` reads that middle status
    from a search head as ``no-hits-both-revisions``, so the numbers are the
    tools' and not this matcher's own.

    Read here rather than run, and that is the whole of the repair: ``grep`` is
    a program a POSIX shell's PATH carries and a Windows shell's does not, so
    executing it graded the host. The same tree gave this repository's own suite
    exit 0 from Git Bash and exit 1 from PowerShell, the twenty differences
    being ``unrunnable-oracle`` standing where each fixture's own finding
    belonged. Nothing about a cut changes with the shell the check was launched
    from, so the search heads are answered in the interpreter already running
    and every host reads one verdict.

    The copy is the whole of what a span reads. An operand rooted outside the
    tree or climbing out of it is no operand at all, and a directory is read
    only where the span asks for recursion -- which ``rg`` asks for by default
    and ``grep`` asks for with ``-r``.
    """

    span = _search_span(argv)
    if span is None:
        return SEARCH_ERROR
    letters, pattern, operands = span
    matcher = _search_matcher(letters, pattern)
    if matcher is None:
        return SEARCH_ERROR
    recursive = bool(letters & {"r", "R"}) or argv[0] == "rg"
    # A recursive search naming no operand reads the working directory --
    # ``rg`` by default, ``grep -r`` since 2.11 -- and the working directory
    # is the copy.
    if not operands and recursive:
        operands = ["."]
    inverted = "v" in letters
    selected = False
    # A span naming nothing to read decided nothing, which is the error status
    # and not the absence of a match.
    failed = not operands
    for operand in operands:
        here = _inside_the_copy(tree, operand)
        if here is None:
            failed = True
        elif here.is_dir():
            if recursive:
                for path in _files_under(here):
                    hit = _selected(matcher, path, inverted)
                    failed = failed or hit is None
                    selected = selected or hit is True
            else:
                failed = True
        else:
            hit = _selected(matcher, here, inverted)
            failed = failed or hit is None
            selected = selected or hit is True
    # grep's own exception, stated in its manual: under ``-q`` a selected line
    # exits 0 even where an error occurred, because the question was only
    # whether anything matched.
    if failed and not (selected and "q" in letters):
        return SEARCH_ERROR
    return 0 if selected else NO_MATCH


def _unreadable_search(command):
    """Is this a search span whose options this tool's own matcher cannot read?

    Asked at extraction, so such a span is reported the way a shell-headed one
    is -- as the criterion's extraction gap, which is advisory and settles
    nothing -- rather than run under a guess at what the option meant.
    """

    head = command.split()[:1]
    if not head or head[0] not in SEARCH_HEADS:
        return False
    try:
        argv = shlex.split(command)
    except ValueError:
        return True
    return not argv or _search_span(argv) is None


def _verdict_in_output(command):
    """Is this a command whose exit status carries no verdict?

    ``grep -c`` prints a count and exits on whether it printed anything. A
    criterion saying "reports 0" is judged by that text, which no exit status
    carries, so the honest report is that cutcheck cannot decide it. The git
    command that reads the same way is owned here now that the scratch copy
    carries history and its head excuses nothing: ``git rev-list --count``
    prints the number and exits 0 whatever it counted.
    """

    argv = command.split()
    if argv[0] == GIT_HEAD:
        return GIT_COUNT_FLAG in argv[1:]
    if argv[0] not in SEARCH_HEADS:
        return False
    return any(COUNT_FLAG_RE.match(token) for token in argv[1:])



# The gate's row, read as the tokens that identify each of the five checks
# `AGENTS.md` requires. An oracle naming a fixed input whose value holds one of
# them is stating the gate's row through a name, which is the one spelling the
# command-shaped reading above cannot see.
REQUIRED_SCRIPTS = frozenset({"validate.py", "run_serial_compat.py"})
SHARD_RUNNER = "run_tests.py"
DRY_RUN = ("install.py", "--dry-run")
DIFF_CHECK = ("git", "diff", "--check")
# `tools/run_tests.py` is the one required check that also spells a unit's own
# focused oracle, so the name alone decides nothing about it: a run naming what
# it runs -- through `--scope` or through a positional module -- is the oracle
# the unit policy asks for, and convicting it would convict every honest unit.
SELECTION_FLAG = "--scope"
# A value states several commands and each is read where it stands: a shard
# runner in one clause and a `--scope` in the next are two commands, not one
# selected run.
SEGMENT_RE = re.compile(r"[;,\n]")
INPUT_PREFIX = "- input: "
# A name is named, never merely spelled inside a longer one: `focused` must not
# be found in `focused-regression`, and the separator these names carry is a
# word character to no regular expression that does not say so.
NAME_EDGE = r"(?<![0-9A-Za-z_-]){}(?![0-9A-Za-z_-])"


def _value_tokens(segment):
    """One segment's argv-ish tokens, punctuation and path separators evened out."""

    return [token.strip("`\"'.()").replace("\\", "/") for token in segment.split()]


def _selects_its_shards(tokens, index):
    """Does this shard-runner invocation name which shards it runs?"""

    return any(
        token == SELECTION_FLAG or not token.startswith("-")
        for token in tokens[index + 1:]
    )


def _required_check(segment):
    """Is this segment one of the five checks the standards owner requires?

    Read on what stands in the segment rather than on an exact spelling: the
    interpreter in front differs by host, `python`, `python3` and `uv run
    --no-project python` all being the same check, and the value is prose that
    happens to hold a command rather than a command line.
    """

    tokens = _value_tokens(segment)
    names = [token.rsplit("/", 1)[-1] for token in tokens]
    present = set(tokens) | set(names)
    if present & REQUIRED_SCRIPTS:
        return True
    if all(part in present for part in DRY_RUN):
        return True
    if all(part in present for part in DIFF_CHECK):
        return True
    if SHARD_RUNNER in names:
        return not _selects_its_shards(tokens, names.index(SHARD_RUNNER))
    return False


def _whole_suite_value(value, tree):
    """The segment of this literal value that names a whole-suite run, or None.

    The same question `_whole_suite` asks of a command, asked of the text a
    fixed input holds: is, or contains, one of the five required checks, a
    shard-runner invocation naming no shard, or a test invocation naming no
    node id. The segment is returned rather than a bare yes so the report can
    name which half of the value earned the finding.
    """

    if not isinstance(value, str):
        return None
    for segment in SEGMENT_RE.split(value):
        segment = segment.strip()
        if segment and (_required_check(segment) or _whole_suite(segment, tree)):
            return segment
    return None


def _input_literals(section):
    """``{name: value}`` for every literal record this Fixed-inputs section holds.

    Read leniently: whether a record is canonical, complete or unique is the
    admission layer's finding and is reported there. What is asked here is
    narrower -- which name stands for which literal text -- and a record that
    would fail admission still answers it.
    """

    literals = {}
    for line in section.splitlines():
        line = line.strip()
        if not line.startswith(INPUT_PREFIX):
            continue
        try:
            record = _syntax.parse_canonical_json(line[len(INPUT_PREFIX):])
        except (TypeError, ValueError):
            continue
        if not isinstance(record, dict) or record.get("type") != "literal":
            continue
        name, value = record.get("name"), record.get("value")
        if isinstance(name, str) and isinstance(value, str):
            literals[name] = value
    return literals


def _indirect_whole_suite(criterion, literals, tree):
    """``(name, segment)`` where this criterion's oracle names its acceptance.

    An oracle may state its command or name the fixed input holding it, and the
    second spelling ran unread: "run the `acceptance-as-runnable-checks` fixed
    input" carries no command head, so it left the report as an extraction gap
    while naming the whole gate's row. The record is resolved by name and its
    value read with the same detector, so both spellings reach one verdict.

    The oracle field alone, never the prose beside it. A criterion cites the
    policy it works under and states its own focused check, and policy prose
    holds commands: this run's `unit-oracle-policy` states `git diff --check`
    inside its value. Reading the whole criterion convicted the citation, and
    this class sets the exit status, so the cost of that reading is an honest
    cut refused.
    """

    stated = _syntax.ORACLE_RE.search(criterion)
    if stated is None:
        return None
    oracle = stated.group(1)
    for name in sorted(literals):
        if not re.search(NAME_EDGE.format(re.escape(name)), oracle):
            continue
        segment = _whole_suite_value(literals[name], tree)
        if segment is not None:
            return name, segment
    return None


__all__ = (
    '_search_span', '_search_matcher', '_selected', '_files_under',
    '_inside_the_copy', '_search_exit', '_unreadable_search', '_verdict_in_output',
    '_whole_target', '_filter_narrows', '_whole_suite', '_value_tokens',
    '_selects_its_shards', '_required_check', '_whole_suite_value',
    '_input_literals', '_indirect_whole_suite',
)
