"""Loss-vocabulary and source-roster parsing support."""

from __future__ import annotations

import ast
import re
from pathlib import Path

from super_research import runner, transport
from super_research.adapters import youtube_innertube
from tests import test_keyless
from tests.test_keyless import roster_manifest

from .support import (
    ADAPTER_DIR,
    CORE_MODULES,
    PACKAGE_DIR,
    TESTS_DIR,
    branch_targets,
    package_sources,
    parsed,
    public_module_name,
)

PROTOCOL_PATH = TESTS_DIR.parent / "references" / "protocol.md"

# The loss tables in `protocol.md`, named by the header row each carries — a
# count of them here would be one more sentence nothing reads, and the two that
# stood in this file already disagreed with each other.
# Only tables with this shape are read; every other table in that file belongs
# to someone else.
LOSS_TABLE_HEADERS = ("| code | means | named by |",)

# A code the tables may name that the source is expected not to contain at all.
# Both are vocabulary the spec added for routes that are deferred, so their
# absence is the statement rather than a gap — but it is a statement, so it is
# checked in that direction too.
UNSHIPPED_CODES = ("archive_lag", "scope_required")

# Modules that declare a loss code as a constant and never load it, which is a
# claim rather than an oversight and is therefore pinned in that direction too.
# `reddit_feed`, `rss_atom`, `public_page` and `github_rest` declare
# `AUTH_REQUIRED` and load it nowhere because no status a documented-keyless
# route can answer with is a report that a credential was needed; `transport`
# and `cache` each own a code for the module that attaches it. A name with zero
# loads is only checkable from outside the module if something checks it.
DECLARED_NEVER_LOADED = {
    "auth_required": ("github_rest", "public_page", "reddit_feed", "rss_atom"),
    "rate_limited": ("transport",),
    "cache_hit": ("cache",),
    "unreachable": ("transport",),
}


def module_name(path):
    """What `protocol.md` calls this module: an adapter by its id, else its stem."""

    return public_module_name(path)


def loss_table_rows():
    """Every row of the loss tables, as (code, cell) pairs in document order.

    Parsed rather than transcribed: the point of the exercise is that the table
    a reader reads is the one the assertions run against, so a cell nobody
    re-read after an adapter edit is a red test.
    """

    rows = []
    inside = False
    for line in PROTOCOL_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped in LOSS_TABLE_HEADERS:
            inside = True
            continue
        if inside:
            if not stripped.startswith("|"):
                inside = False
                continue
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if set(cells[0]) <= set("- "):
                continue
            rows.append((backticked(cells[0]), cells[-1]))
    return rows


def backticked(text):
    """Every ``name`` in one cell, dotted names cut back to the module they name."""

    found = []
    for index, piece in enumerate(text.split("`")):
        if index % 2 and piece:
            found.append(piece.split(".")[0])
    return tuple(found)


def declared_loss_constants(codes):
    """Package-wide: constant name -> loss code, from module-level ``NAME = "code"``."""

    named = {}
    for path in package_sources():
        for node in parsed(path).body:
            if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Constant):
                continue
            if node.value.value in codes and len(node.targets) == 1:
                if isinstance(node.targets[0], ast.Name):
                    named[node.targets[0].id] = node.value.value
    return named


def names_a_loss_code(path, codes, constants):
    """Which of ``codes`` this module's executable syntax spells, and which it only declares.

    A declaration is exactly ``NAME = "code"`` at module level, so a literal
    inside a ``DESCRIPTOR = AdapterDescriptor(standing_loss=(...))`` call is an
    emission and not a declaration. Everything else that reaches the code counts:
    a bare literal, a load of a constant this package bound to it, or an
    attribute load of one another module owns.
    """

    tree = parsed(path)
    declarations = {
        id(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and isinstance(node.value, ast.Constant)
        and node.value.value in codes
    }
    spelled = set()
    declared = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and node.value in codes:
            (declared if id(node) in declarations else spelled).add(node.value)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            if constants.get(node.id) in codes:
                spelled.add(constants[node.id])
        elif isinstance(node, ast.Attribute) and constants.get(node.attr) in codes:
            spelled.add(constants[node.attr])
    return (spelled, declared - spelled)


def loss_code_spelling(codes):
    """code -> the modules that spell it, and code -> the modules that only declare it."""

    constants = declared_loss_constants(codes)
    spelling = {code: set() for code in codes}
    declaring = {code: set() for code in codes}
    for path in package_sources():
        spelled, declared_only = names_a_loss_code(path, codes, constants)
        for code in spelled:
            spelling[code].add(module_name(path))
        for code in declared_only:
            declaring[code].add(module_name(path))
    for code in codes:
        declaring[code] -= spelling[code]
    return (spelling, declaring)


# Number words a heading or a docstring in this delivery may count in. The
# checks below read it: the shortfall heading in `protocol.md`, this file's own
# module count, what the reference documents state about the roster, and what
# `test_keyless` states about `auth_required`. It runs at least as far as the
# roster is wide, because the widest of those counts adapters — a table that
# stopped short would read a lawful count as an unspellable one.
NUMBER_WORDS = (
    "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
    "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen",
    "Eighteen", "Nineteen", "Twenty",
)

# The tens, for the counts this delivery states past the flat table's end: the
# roster's route-surface total, and the count of it that is read. A tens name
# means its own position in tens, and a compound is its two names read the same
# way — `forty-two` is `forty` and `two`, chosen as the example because nothing
# in this delivery counts it and so nothing can make this line false.
TENS_WORDS = ("Ten", "Twenty", "Thirty", "Forty", "Fifty")


ITEM_DIR = TESTS_DIR.parent
OWNER_SKILL = ITEM_DIR / "SKILL.md"
# The checkout root a generated adapter's pointer is relative to
# (`orchflows_adapters.pointer_for`), not the stub's own directory.
PROJECT_ROOT = ITEM_DIR.parent.parent.parent
HOST_MIRROR = PROJECT_ROOT / ".claude" / "skills" / "super-research" / "SKILL.md"

# `rules/composition.md` §5. Restated rather than imported because
# `tools/validate.py`, which enforces it for every library skill, does not read
# `.orchflows/` at all: a project-scope item's frontmatter has no other oracle.
DESCRIPTION_BUDGET = 140


def frontmatter_description(path):
    """One skill's ``description:`` field, read out of its frontmatter alone.

    The block, not the file: the mirror's body is prose *about* the include, and
    a sentence there beginning with the word would otherwise answer for a field
    the frontmatter had lost.
    """

    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() == "---":
            return None
        if line.startswith("description:"):
            return line.split(":", 1)[1].strip()
    return None


OPERATING_PATH = TESTS_DIR.parent / "references" / "operating.md"

# The phrase both documents count the multi-surface adapters with, and the
# whole of what this reads them by. An anchor rather than either sentence: the
# two paragraphs are written in different voices and are meant to stay that
# way, so a pin that matched the prose around the number would forbid the
# rewrite it is supposed to permit.
MULTI_SURFACE_ANCHOR = re.compile(
    r"\b([A-Za-z]+(?:-[A-Za-z]+)?) adapters rea(?:d|ch) more than one\b"
)

# The other two counts that one roster sentence states. Anchored the same way and
# for the same reason: "seven" went stale for three adapters while a reader was
# the only thing checking it, and these two were still that reader's. Each phrase
# is the part of the sentence the count cannot leave, not the sentence.
ROSTER_SIZE_ANCHOR = re.compile(
    r"\b([A-Za-z]+(?:-[A-Za-z]+)?) adapters, ([A-Za-z]+(?:-[A-Za-z]+)?) live plus `fake`"
)
SURFACE_TOTAL_ANCHOR = re.compile(r"\b([A-Za-z]+(?:-[A-Za-z]+)?) route surfaces\b")

# The same paragraph states that total a second time, two lines down, and
# derives a count from it: "Thirty-five of the thirty-six are read". The anchor
# above reaches neither, because the phrase it pins on is `route surfaces` and
# this sentence does not spell it — so the paragraph stated the total twice and
# one statement was checked, which is the drift this suite exists to stop
# living inside the paragraph the pin reads. This is the second statement's own
# anchor: the phrase its two counts cannot leave, whitespace-tolerant because
# the document wraps between them.
READ_SURFACE_ANCHOR = re.compile(
    r"\b([A-Za-z]+(?:-[A-Za-z]+)?)\s+of\s+the\s+([A-Za-z]+(?:-[A-Za-z]+)?)\s+are\s+read\b"
)

# The same count where `surface_descriptors` states it about itself. Its own
# paragraph rather than either document's, so its own anchor: the two words the
# count cannot leave while the sentence still says that some adapters are the
# exception. A word this cannot read counts as none and fails, the way the
# document anchors do.
RESOLVER_COUNT_ANCHOR = re.compile(r"\b([A-Za-z]+(?:-[A-Za-z]+)?) do not\b")

# The two counts `test_keyless`' module docstring states about `auth_required`:
# how many adapters name the code at all, and how many of those can say it.
# It counted once, and the one number was wrong in both directions — the same
# class as the roster's "seven", one file over, and the loss tables beside it
# already read which modules spell each code. One anchor each, on the phrase
# the count cannot leave rather than on the sentence, because that paragraph is
# written in its own voice and is meant to stay that way.
# Whitespace-tolerant for the reason the read-surface anchor is: a paragraph
# wraps where its width puts it, and a pin that forbade a wrap point would be
# pinning the layout rather than the count.
KEYLESS_NAMING_ANCHOR = re.compile(r"\b([A-Za-z]+)\s+adapters\s+name\s+it\b")
KEYLESS_SAYING_ANCHOR = re.compile(r"\b([A-Za-z]+)\s+of\s+them\s+can\s+say\s+it\b")

# The one roster row read cell by cell here. Its adapter id comes off the
# module that owns the route rather than off this file, so a rename reaches
# the assertions.
YOUTUBE = youtube_innertube.DESCRIPTOR.adapter_id

# What a cell can deny a subject with, and the subject this row was caught
# denying: it ended "No captions" while the transcript operation beside it was
# reading a caption track. A denial is checked per clause rather than per
# cell, because a row is allowed to say that some other surface has none.
DENIALS = ("no", "not", "never", "without", "none")
CAPTION_WORDS = ("caption", "captions", "transcript", "transcripts")


def denied_in(cell, subjects):
    """Every clause of one cell that names a subject and denies it in one breath."""

    found = []
    for clause in re.split(r"[.;,]", cell):
        words = [word.strip("`*_()[]'\"").lower() for word in clause.split()]
        if any(subject in words for subject in subjects):
            if any(denial in words for denial in DENIALS):
                found.append(clause.strip())
    return found

# The adapter roster in `protocol.md`, named by its header row the way the loss
# tables above are named by theirs.
ROSTER_TABLE_HEADER = "| adapter | class | route surfaces | what ships |"


def roster_table_rows():
    """The adapter roster, keyed by adapter id, each row column name -> cell.

    Parsed rather than transcribed, for the reason the loss tables are: the
    row a reader reads is the row the assertions run against.
    """

    rows = {}
    columns = None
    for line in PROTOCOL_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped == ROSTER_TABLE_HEADER:
            columns = [cell.strip() for cell in stripped.strip("|").split("|")]
            continue
        if columns is None:
            continue
        if not stripped.startswith("|"):
            break
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if set(cells[0]) <= set("- "):
            continue
        named = backticked(cells[0])
        if len(named) == 1:
            rows[named[0]] = dict(zip(columns, cells))
    return rows


def counted_as(word):
    """The number one spelled number word names, or ``None`` if it names none.

    Spelling first: `NUMBER_WORDS` and `TENS_WORDS` are lists of names, and no
    count this file checks is written down here — every one of them comes off
    the descriptors. The only arithmetic is what a tens name means, its own
    position in tens; a hyphenated compound is its head and its tail looked up
    the same way, which is how a count past the flat table's end is spelled at
    all.
    """

    spelled = [name.lower() for name in NUMBER_WORDS]
    tens = [name.lower() for name in TENS_WORDS]
    head, _, tail = word.lower().partition("-")
    if not tail and head in spelled:
        return spelled.index(head) + 1
    if head in tens:
        counted = (tens.index(head) + 1) * 10
        if not tail:
            return counted
        if tail in spelled[:9]:
            return counted + spelled.index(tail) + 1
    return None


def multi_surface_adapters():
    """Every adapter the source gives more than one route surface."""

    return {
        adapter_id
        for adapter_id in runner.ADAPTER_IDS
        if len(runner.surface_descriptors(adapter_id)) > 1
    }


def resolver_chain_ids():
    """Every adapter id the ``surface_descriptors`` chain answers for itself.

    Read off the branches rather than off the descriptors, because the claim
    the docstring above them makes is a claim about the lines under it: the
    exceptions it counts are exactly the ids that chain spells.
    """

    return tuple(
        adapter_id
        for adapter_id, _, _ in branch_targets(PACKAGE_DIR / "runner.py", "surface_descriptors")
    )


def live_adapters():
    """Every declared adapter that reads an origin rather than a fixture.

    Read off the class the descriptor declares rather than off the one id a
    reader knows: the roster counts `fake` apart because it is `offline`, and
    that is where the fact lives.
    """

    found = set()
    for adapter_id in runner.ADAPTER_IDS:
        descriptor = runner.descriptor_for(adapter_id)
        if descriptor is not None and descriptor.access_class != "offline":
            found.add(adapter_id)
    return found


def surface_total():
    """Every route surface the source declares, across the whole roster."""

    return sum(len(runner.surface_descriptors(adapter_id)) for adapter_id in runner.ADAPTER_IDS)


def read_surface_total():
    """Every declared surface a caller reads: the roster's, less the activations.

    ``transport.TOKEN_ACTIVATION_ROUTES`` is where this package says which
    routes are spent rather than read, so it is what this counts by. Naming
    `x_guest`'s activation here instead would be a second transcription of the
    fact the paragraph under test already transcribes once.
    """

    return sum(
        1
        for adapter_id in runner.ADAPTER_IDS
        for descriptor in runner.surface_descriptors(adapter_id)
        if descriptor.route_id not in transport.TOKEN_ACTIVATION_ROUTES
    )


def adapters_naming_the_refusal():
    """Who names `auth_required`, who can say it, and every module that says it.

    Read by the scan the loss tables already run over every code `protocol.md`
    tables, because the distinction the keyless docstring rests on is exactly
    the one that scan draws: a module-level ``NAME = "code"`` and nothing else
    is a declaration, everything that reaches the code is an emission. A module
    that only mentions the string in its prose names it in neither sense, which
    is why this reads syntax and not text — `hacker_news` spells the code once,
    in a sentence saying it deliberately has no such branch.
    """

    code = test_keyless.AUTH_REQUIRED
    spelling, declaring = loss_code_spelling({code})
    roster = set(runner.ADAPTER_IDS)
    return (
        (spelling[code] | declaring[code]) & roster,
        spelling[code] & roster,
        spelling[code],
    )


def multi_surface_counts_in(text):
    """Every multi-surface count one passage states, in reading order.

    Text rather than a path, because one of the passages is a docstring: the
    sentence is the subject either way, and where it is kept is not.
    """

    return tuple(
        counted_as(match.group(1)) for match in MULTI_SURFACE_ANCHOR.finditer(text)
    )
