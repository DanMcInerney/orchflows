"""Price what a cut grows, and refuse a root its own pack cannot execute.

Family 3's second half. ``cutcheck_ticket`` owns the four screens that read
what a cut *says*; these six read what it *costs*, and they live here because
that module stands close enough to its own size ceiling that the arithmetic
below would have pushed it over -- which is, exactly, screen 2's subject.

Each is one sentence:

1. ``_unpriced_growth`` -- a cut that prices one file its objective grows and
   skips another. Partial pricing, never absent pricing: a cut whose files sit
   nowhere near a ceiling owes no arithmetic, so the screen wakes only once the
   ticket has priced something and is therefore claiming to have measured.
2. ``_unsplittable_owner`` -- an owner closed at its cap with no lawful split
   in the grant. Ordering growth into a file that cannot lawfully grow by one
   line is jointly unsatisfiable as written, and the unit pays the whole bound
   before it finds out.
3. ``_ceiling_without_arithmetic`` -- a numeric ceiling asserted over a granted
   file with no size beside it. Stating the cap and not the distance to it
   moves the measuring onto the unit.
4. ``_unpinned_output`` -- an objective changing what a granted module emits,
   while the checks pinning that output lie outside the grant. The item cannot
   land without breaking them and is not licensed to repair them.
5. ``_pack_admissible`` -- a pack-stamped root whose own workspace cell forbids
   the isolation the root fixes. The executor the pack binds cannot be admitted
   under it, and the contradiction surfaces one respec cycle at a time.
6. ``_excluded_required`` -- an exact required command whose program tokens
   spell an action the same root excludes. Token-level and structured-only: it
   flags the collision and judges nothing about what the command would do.

All six report outside the advisory set. Advisory membership is a frozen
contract constant this module is not the owner of, and each of these names a
contradiction the cut carries rather than a weak reading of one: every instance
below was paid for by a unit that lost time to a cut which had already passed.
"""

import json

try:  # repository checkout
    from scripts import cutcheck_contract as _contract
except ImportError:  # installed flat script directory
    import cutcheck_contract as _contract

try:  # repository checkout
    from scripts import cutcheck_scope as _scope
except ImportError:  # installed flat script directory
    import cutcheck_scope as _scope

try:  # repository checkout
    from scripts import cutcheck_executor as _executor
except ImportError:  # installed flat script directory
    import cutcheck_executor as _executor

re = _contract.re
Path = _contract.Path
FAMILY_3 = _contract.FAMILY_3
FAMILY_OF = _contract.FAMILY_OF

UNPRICED_GROWTH = "unpriced-growth"
UNSPLITTABLE_OWNER = "unsplittable-owner"
CEILING_WITHOUT_ARITHMETIC = "ceiling-without-arithmetic"
UNPINNED_OUTPUT = "unpinned-output"
PACK_INADMISSIBLE_ROOT = "pack-inadmissible-root"
EXCLUDED_REQUIRED_COMMAND = "excluded-required-command"
SCREENS = (
    UNPRICED_GROWTH, UNSPLITTABLE_OWNER, CEILING_WITHOUT_ARITHMETIC,
    UNPINNED_OUTPUT, PACK_INADMISSIBLE_ROOT, EXCLUDED_REQUIRED_COMMAND,
)
for _screen in SCREENS:
    # Registered from the judgment's own module, the way `cutcheck_ticket`
    # registers its four. `setdefault`, so a contract adopting one of these
    # names later owns it and this line decides nothing.
    FAMILY_OF.setdefault(_screen, FAMILY_3)

# "429 of 510" is the whole of the arithmetic a price has to state; a headroom
# beside it is the same fact subtracted, and either one answers the screen.
PRICE_RE = re.compile(r"\b(\d{1,6})\s+of\s+(\d{1,6})\b")
HEADROOM_RE = re.compile(r"\bheadroom\s+(-?\d{1,6})\b", re.I)
CEILING_RE = re.compile(r"\b(?:ceiling|cap|caps|capped|limit|budget)\b", re.I)
# How far back a price looks for the path it is a price of, and how wide a
# ceiling looks for both. A Fixed inputs section states its anchors in one
# sentence per file, so the subject is the nearest path behind the number.
PRICE_WINDOW = 160
CEILING_WINDOW = 160
CHANGE_VERB = "change"
CREATE_VERB = "create"


def _mutation_targets(frontmatter, verb):
    """The paths this cut's own mutation plan marks with ``verb``.

    Read off the plan rather than off the prose: an objective says what the
    work means and the plan says which files it lands in, and pricing is a
    question about files.
    """

    targets = []
    for entry in _scope._listed(frontmatter, "mutations"):
        stated, _, path = entry.partition(":")
        if stated.strip().lower() == verb and path.strip():
            targets.append(path.strip())
    return targets


def _priced(inputs):
    """Every path this ticket states a size and a ceiling for.

    The nearest path behind the arithmetic is its subject. A price with no
    path behind it prices the run rather than a file and is nobody's here.
    """

    flat = _scope._flat(inputs)
    priced = {}
    for match in PRICE_RE.finditer(flat):
        behind = _scope._paths_in(flat[max(0, match.start() - PRICE_WINDOW):match.start()])
        if behind:
            priced.setdefault(behind[-1], (int(match.group(1)), int(match.group(2))))
    return priced


def _unpriced_growth(frontmatter, inputs):
    """Screen 1: pricing that skips a file the objective grows.

    Test modules are counted like any other file, because the module a cut
    forgets to price is the test module: a unit's suite grows with the source
    it grades, and a ceiling reached there stops the work just as hard.
    """

    priced = _priced(inputs)
    if not priced:
        # A cut that priced nothing claims no measurement and is asked for
        # none. Asking every cut for arithmetic would report the whole corpus.
        return []
    subjects = list(priced)
    return [
        (UNPRICED_GROWTH, "{} is grown and never priced, while {} is".format(
            target, min(subjects)))
        for target in _mutation_targets(frontmatter, CHANGE_VERB)
        if not _scope._covered(target, subjects)
    ]


def _unsplittable_owner(frontmatter, inputs):
    """Screen 2: an owner at its cap with no lawful split destination granted.

    A grant of the full file is no licence to exceed its ceiling, so a growing
    owner standing at the cap needs a sub-owner path -- a new file beside it,
    in the grant and in the mutation plan -- or the objective orders a write
    that cannot lawfully be made.
    """

    scope = _scope._listed(frontmatter, "write_scope")
    created = _mutation_targets(frontmatter, CREATE_VERB)
    grown = _mutation_targets(frontmatter, CHANGE_VERB)
    findings = []
    for owner, (size, ceiling) in sorted(_priced(inputs).items()):
        if size < ceiling or not _scope._covered(owner, grown):
            continue
        parent = owner.rpartition("/")[0]
        if any(path != owner and path.rpartition("/")[0] == parent
               and _scope._covered(path, scope) for path in created):
            continue
        findings.append((UNSPLITTABLE_OWNER, "{} is {} of {} and the grant holds no"
                         " split destination beside it".format(owner, size, ceiling)))
    return findings


def _ceiling_without_arithmetic(frontmatter, inputs):
    """Screen 3: a ceiling asserted over a granted file with no size beside it.

    Scoped to the grant on purpose. A word budget or a bound stated about the
    run at large commits no owner to an arithmetic anybody could state, and
    reading those as prices would report every ticket that mentions a limit.
    """

    flat = _scope._flat(inputs)
    scope = _scope._listed(frontmatter, "write_scope")
    findings, seen = [], set()
    for match in CEILING_RE.finditer(flat):
        window = flat[max(0, match.start() - CEILING_WINDOW):match.end() + CEILING_WINDOW]
        if PRICE_RE.search(window) or HEADROOM_RE.search(window):
            continue
        for target in _scope._paths_in(window):
            if target in seen or not _scope._covered(target, scope):
                continue
            seen.add(target)
            findings.append((CEILING_WITHOUT_ARITHMETIC, "{}: a ceiling stated at {!r}"
                             " with no size beside it".format(target, match.group(0))))
    return findings


# What an objective claims when it changes what something emits. Graded on the
# claim rather than on the change: an objective altering an internal call
# orders nothing about anybody's output, and asking every change for a pin
# census would report a cut for every test that imports its owner.
OUTPUT_RE = re.compile(
    r"\b(?:emit|emits|emitted|emitting|output|outputs|prints?|printed"
    r"|renders?|rendered)\b", re.IGNORECASE)


def _unpinned_output(frontmatter, objective, tree):
    """Screen 4: the checks pinning an output this cut changes, left ungranted.

    Over ``tests/`` alone and over the module's own name, which is what a check
    reaches for: a suite that asserts a shape imports the module that emits it.
    """

    if tree is None or not OUTPUT_RE.search(_scope._flat(objective)):
        return []
    scope = _scope._listed(frontmatter, "write_scope")
    names = set()
    for owner in _mutation_targets(frontmatter, CHANGE_VERB):
        if not _scope._covered(owner, scope):
            continue
        base = owner.rsplit("/", 1)[-1]
        names.add(base)
        if base.endswith(".py"):
            names.add(base[:-3])
    if not names:
        return []
    findings = []
    for rel, text in _scope._pin_index(tree):
        if not rel.startswith("tests/") or _scope._covered(rel, scope):
            continue
        hits = [name for name in names if _scope._pins(name, text)]
        if hits:
            findings.append(
                (UNPINNED_OUTPUT, "{} pins {}".format(rel, max(hits, key=len))))
    return findings


# The pack cell's own spelling of what isolation it binds, read out of the
# workspace row. A cell naming no isolation binds none and grades nothing.
PACK_ISOLATION_RE = re.compile(r"isolation:\s*([^;|]+)", re.IGNORECASE)
NO_ISOLATION = "none"
PACKS_DIR = "packs"
_PACK_ISOLATION = {}


def _lib_root():
    """The orchflows library whose pack cells this screen reads, or None.

    Family 6's resolution, reached through its own module so the two screens
    never disagree about which library a pack cell came from. ``cutcheck``
    injects the directory name at its own ``_lib_root``; a caller reaching the
    screens without passing through that entry point would otherwise resolve
    against nothing.
    """

    if _executor.PACKS_DIR is None:
        _executor.PACKS_DIR = PACKS_DIR
    return _executor._lib_root(None)


def _pack_isolation(pack):
    """What the pack's workspace cell binds isolation to, or None.

    Read from the orchflows library, never from the repository under test, for
    the reason family 6 reads it there: a pack cell is a fact about orchflows
    and the tree under test is whatever repository the work lands in.
    """

    if pack in _PACK_ISOLATION:
        return _PACK_ISOLATION[pack]
    found = None
    lib_root = _lib_root()
    if lib_root is not None and _contract.PACK_NAME_RE.match(pack):
        path = Path(lib_root) / PACKS_DIR / pack / "SKILL.md"
        if path.is_file():
            match = PACK_ISOLATION_RE.search(
                path.read_text(encoding="utf-8", errors="replace"))
            if match:
                found = _scope._flat(match.group(1))
    _PACK_ISOLATION[pack] = found
    return found


def _pack_admissible(frontmatter, is_root):
    """Screen 5: a root whose own pack forbids the isolation it fixes.

    The root is where this has to be caught. Its isolation field is what every
    unit inherits, so a root fixing an isolation the pack's bound executor
    cannot be admitted under respecs the whole cut rather than one item.
    """

    pack = str(frontmatter.get("pack") or "").strip()
    isolation = str(frontmatter.get("isolation") or "").strip().lower()
    if not is_root or not pack or isolation != NO_ISOLATION:
        # Read before the library is resolved, and that order is the point:
        # resolving reports when it finds no library, and a reading no cut
        # needed must not put a line in anybody's report.
        return []
    bound = _pack_isolation(pack)
    if not bound or NO_ISOLATION in bound.lower():
        return []
    return [(PACK_INADMISSIBLE_ROOT, "root fixes isolation {!r} while {}'s workspace"
             " cell binds isolation to {!r}".format(isolation, pack, bound))]


ACCEPTANCE_INPUT = "acceptance-as-runnable-checks"
INPUT_RECORD_RE = re.compile(r"^\s*-\s*input:\s*(\{.*\})\s*$", re.M)
# Only a structured action contributes tokens. A sentence of policy holds every
# ordinary word in the language, and reading those as program tokens would flag
# the acceptance of every root ever cut.
STRUCTURED_ACTION_RE = re.compile(r"^[a-z][a-z0-9]*(?:\.[a-z0-9][a-z0-9-]*)+$")
ACTION_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9-]*")
# The namespace half of `vcs.push` names the authority, not the act. Matching on
# it would read every git span as the excluded one.
ACTION_NAMESPACES = frozenset({"vcs", "fs", "net", "run", "sink", "state"})
ACTION_TOKEN_FLOOR = 3


def _required_commands(inputs):
    """The exact commands this root states as its acceptance."""

    found = []
    for match in INPUT_RECORD_RE.finditer(inputs):
        try:
            record = json.loads(match.group(1))
        except ValueError:
            continue
        if not isinstance(record, dict) or record.get("name") != ACCEPTANCE_INPUT:
            continue
        value = record.get("value")
        found.extend(v for v in ([value] if isinstance(value, str) else value or [])
                     if isinstance(v, str))
    return found


def _action_tokens(frontmatter):
    """The act each structured excluded action names, minus its namespace."""

    tokens = set()
    for action in _scope._listed(frontmatter, "excluded_actions"):
        if STRUCTURED_ACTION_RE.match(action.strip()):
            tokens.update(ACTION_TOKEN_RE.findall(action.strip().lower()))
    return {token for token in tokens
            if len(token) >= ACTION_TOKEN_FLOOR and token not in ACTION_NAMESPACES}


def _program_tokens(command):
    """A span's head and the subcommands standing before its first flag."""

    try:
        argv = _contract.shlex.split(command)
    except ValueError:
        return set()
    if not argv:
        return set()
    tokens = {Path(argv[0]).name.lower()}
    for token in argv[1:]:
        if token.startswith("-"):
            break
        tokens.add(Path(token).name.lower())
    return tokens


def _excluded_required(frontmatter, inputs, is_root):
    """Screen 6: a required command spelling an act the same root excludes.

    Flag, never judge: this reads tokens and says they collide. Whether the
    span would really perform the excluded act is a question about the program,
    and the one instance that paid for this passed at exit 0 while nobody asked
    it. Naming the collision is what the reader needed.
    """

    if not is_root:
        return []
    excluded = _action_tokens(frontmatter)
    if not excluded:
        return []
    findings = []
    for command in _required_commands(inputs):
        collide = sorted(_program_tokens(command) & excluded)
        if collide:
            findings.append((EXCLUDED_REQUIRED_COMMAND, "{}: required, and its own"
                             " exclusions name {}".format(command, ", ".join(collide))))
    return findings


def screens(frontmatter, objective, inputs, tree, is_root):
    """Every reading above, in one call, for the assembly that wires them.

    One entry point rather than six, so the module that calls the screens
    spends its remaining headroom on the call and not on the list of them --
    which is the same economy screen 2 grades a cut for failing to make.
    """

    findings = []
    findings.extend(_unpriced_growth(frontmatter, inputs))
    findings.extend(_unsplittable_owner(frontmatter, inputs))
    findings.extend(_ceiling_without_arithmetic(frontmatter, inputs))
    findings.extend(_unpinned_output(frontmatter, objective, tree))
    findings.extend(_pack_admissible(frontmatter, is_root))
    findings.extend(_excluded_required(frontmatter, inputs, is_root))
    return findings


__all__ = (
    'UNPRICED_GROWTH', 'UNSPLITTABLE_OWNER', 'CEILING_WITHOUT_ARITHMETIC',
    'UNPINNED_OUTPUT', 'PACK_INADMISSIBLE_ROOT', 'EXCLUDED_REQUIRED_COMMAND',
    'SCREENS', '_mutation_targets', '_priced', '_unpriced_growth',
    '_unsplittable_owner', '_ceiling_without_arithmetic', '_unpinned_output',
    '_pack_isolation', '_pack_admissible', '_required_commands',
    '_action_tokens', '_program_tokens', '_excluded_required', 'screens',
)
