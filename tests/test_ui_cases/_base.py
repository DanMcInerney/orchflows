"""Reader UI: sink resolution, discovery, escaping, empty states, status
presentation, verification degradation, the elapsed meter, and the
read-only, no-network and loopback-only guarantees."""

import ast
import contextlib
import html
import http.client
import io
import ipaddress
import json
import os
import re
import shutil
import sys
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock
from unittest.mock import patch
from urllib.parse import quote

PAYLOAD = "<script>alert(1)</script>"
# Spec criterion 12: an asset reference is remote when its value starts
# with a scheme or with a protocol-relative `//`.
REMOTE_ASSET_RE = re.compile(r"""(?:src|href)\s*=\s*["']?\s*(?:https?:)?//""", re.IGNORECASE)

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.state_root as state_root  # noqa: E402
import scripts.tickets as tickets_mod  # noqa: E402
import scripts.ui as ui  # noqa: E402

SINK_ENV_VAR = "ORCHFLOWS_STATE_HOME"
UI_PY = ROOT / "scripts" / "ui.py"
WORK_ITEM_CONTRACT = ROOT / "contracts" / "work-item.md"
FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "ui"
FIXTURE_RUNS = ("run-alpha", "run-beta", "run-gamma", "run-delta", "run-epsilon")
EMPTY_RUN = "run-empty"
# Every ticket in `run-delta` is terminal and none is claimed, so it is the
# corpus's settled run: the case where the band is absent and the poll
# interval must not be the live one.
SETTLED_RUN = "run-delta"
CYCLIC_RUN = "run-epsilon"

# The synthetic `~/.claude/projects` tree. `tests/fixtures/transcripts/README.md`
# records what each fixture carries and why.
FIXTURE_TRANSCRIPTS = Path(__file__).resolve().parent.parent / "fixtures" / "transcripts"
ALPHA_PROJECT = "-Users-dmcinerney-tools-alpha"
BETA_PROJECT = "-Users-dmcinerney-tools-beta-repo"
WORKTREE_PROJECT = "-Users-dmcinerney-tools-beta-repo--claude-worktrees-wt-one"
UNDECODABLE_PROJECT = "not-an-encoded-path"

TITLED_SESSION = "11111111-1111-4111-8111-111111111111"
UNTITLED_SESSION = "22222222-2222-4222-8222-222222222222"
MARKUP_SESSION = "33333333-3333-4333-8333-333333333333"
MALFORMED_SESSION = "44444444-4444-4444-8444-444444444444"
TRUNCATED_SESSION = "55555555-5555-4555-8555-555555555555"
EMPTY_SESSION = "66666666-6666-4666-8666-666666666666"

SESSION_PROJECT = {
    TITLED_SESSION: ALPHA_PROJECT,
    UNTITLED_SESSION: ALPHA_PROJECT,
    MARKUP_SESSION: BETA_PROJECT,
    MALFORMED_SESSION: BETA_PROJECT,
    TRUNCATED_SESSION: WORKTREE_PROJECT,
    EMPTY_SESSION: UNDECODABLE_PROJECT,
}

# Deliberately interleaved across the project directories: an index that
# grouped by directory and ordered within it would still satisfy an
# ordering assertion made over one directory's sessions.
SESSIONS_NEWEST_FIRST = (
    MARKUP_SESSION,
    TITLED_SESSION,
    TRUNCATED_SESSION,
    UNTITLED_SESSION,
    MALFORMED_SESSION,
    EMPTY_SESSION,
)
# An hour apart from a fixed instant, so an ordering assertion never
# depends on the second the copy happened to run in.
SESSION_EPOCH = 1780000000
SESSION_STEP = 3600
# Subagent files sit after every session file and a minute apart, so a
# subagent's rendered last activity is distinguishable from its session's
# and from every other subagent's.
AGENT_EPOCH = SESSION_EPOCH + 1800
AGENT_STEP = 60

# Present in every `user` and `assistant` body, every `last-prompt`,
# attachment, tool input, tool result and file-history record in the
# fixture corpus, and in none of its renderable fields.
TRANSCRIPT_SENTINEL = "ZQXJVWNTRPKB-transcript-content-must-not-render"
LAST_AI_TITLE = "Alpha, the last title recorded"
SUPERSEDED_AI_TITLE = "Alpha, the title that was superseded"

# The corpus's subagents, by the shape each one is here to carry.
RETURNED_AGENT = "agent-aa11"
CALLED_AGENT = "agent-aa12"
UNEVIDENCED_AGENT = "agent-aa13"
ALPHA_AGENTS = (RETURNED_AGENT, CALLED_AGENT, UNEVIDENCED_AGENT)
MARKUP_AGENT = "agent-bb21"
BAD_FIELDS_AGENT = "agent-bb22"
UNREADABLE_AGENT = "agent-bb23"
PARENT_AGENT = "agent-cc31"
CHILD_AGENT = "agent-cc32"
MARKUP_AGENT_TYPE = PAYLOAD
# Quote characters as well as angle brackets: an attribute context breaks
# on the quote alone, and `html.escape` is only proved by a value that
# would break both contexts differently.
MARKUP_AGENT_DESCRIPTION = '<img src="x" onerror="alert(1)">'


def contract_statuses() -> tuple:
    """The closed status set exactly as `contracts/work-item.md` states it.

    Read from the contract rather than restated here, so the presentation
    map is held to its owner: a status added there and missed here fails
    this suite instead of rendering as the unknown fallback."""

    text = WORK_ITEM_CONTRACT.read_text(encoding="utf-8")
    declaration = re.search(r"^- `status`:(.+?)—", text, re.MULTILINE | re.DOTALL)
    if declaration is None:
        return ()
    return tuple(re.findall(r"`([a-z]+)`", declaration.group(1)))


def contract_sections() -> tuple:
    """The body section names `contracts/work-item.md` fixes, read from the
    contract for the same reason as the status set."""

    text = WORK_ITEM_CONTRACT.read_text(encoding="utf-8")
    return tuple(re.findall(r"^- `## (.+?)` —", text, re.MULTILINE))


def copy_logs(source: Path, dest: Path):
    """One fixture log directory materialized under a temporary sink."""

    dest.mkdir(parents=True)
    for src in sorted(source.glob("*.jsonl")):
        shutil.copyfile(str(src), str(dest / src.name))


def make_sink(tmp: Path, runs=FIXTURE_RUNS, friction=True, events=True) -> Path:
    """A state sink: ``tickets/<run>/`` materialized from the flat tracked
    fixtures, one run with no tickets (git tracks no empty directory, so it is
    built here), the friction log and the deferred hooks seam's event log.
    ``runs`` narrows the corpus for a test that needs a run set the whole
    corpus does not exhibit. No ``.git`` anywhere: the sink is not in a
    repository, and nothing here may depend on one."""

    root = tmp / "sink"
    tickets = root / "tickets"
    for run in runs:
        dest = tickets / run
        dest.mkdir(parents=True)
        for src in sorted((FIXTURES / run).glob("*.md")):
            shutil.copyfile(str(src), str(dest / src.name))
    (tickets / EMPTY_RUN).mkdir(parents=True)
    if friction:
        copy_logs(FIXTURES / "friction", root / "friction")
    if events:
        copy_logs(FIXTURES / "events", root / "events")
    return root


def fixture_agent_files() -> list:
    """Every subagent file in the corpus, by tree-relative name.

    Derived from the tree rather than listed, so adding a fixture subagent
    never needs a table here kept in step with it.
    """

    return sorted(
        path.relative_to(FIXTURE_TRANSCRIPTS).as_posix()
        for path in FIXTURE_TRANSCRIPTS.rglob("agent-*")
        if path.is_file()
    )


def make_transcripts(tmp: Path) -> Path:
    """The synthetic transcript root, materialized under a temporary
    directory with a deterministic last-activity time per session.

    The index orders on the transcript's mtime and a copy takes whatever
    the clock says, so the order is stamped here rather than inherited from
    the order `copytree` happened to walk in. A subagent's stamp is its own
    file's, for the same reason: the flowchart draws it as a last activity.
    """

    dest = tmp / "transcripts"
    shutil.copytree(str(FIXTURE_TRANSCRIPTS), str(dest))
    for index, session in enumerate(SESSIONS_NEWEST_FIRST):
        stamp = SESSION_EPOCH - index * SESSION_STEP
        path = dest / SESSION_PROJECT[session] / (session + ".jsonl")
        os.utime(str(path), (stamp, stamp))
    for index, name in enumerate(fixture_agent_files()):
        stamp = AGENT_EPOCH + index * AGENT_STEP
        os.utime(str(dest / name), (stamp, stamp))
    return dest


# The year 30828, which is where an NTFS FILETIME runs out. No filesystem
# this suite can write reaches it -- APFS clamps at 2262 -- so the mtime is
# substituted at the one seam that reads one.
FAR_FUTURE_MTIME_NS = 910692730085000000000


@contextlib.contextmanager
def far_future_mtimes():
    """Every file the session views stat, dated past the calendar."""

    real = ui._stat_identity

    def stamped(path):
        identity = real(path)
        return None if identity is None else identity[:2] + (FAR_FUTURE_MTIME_NS,)

    with patch.object(ui, "_stat_identity", stamped):
        yield


def utc_stamp(seconds: int) -> str:
    return datetime.fromtimestamp(seconds, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def session_stamp(session: str) -> str:
    """The last-activity stamp `make_transcripts` gave one session."""

    return utc_stamp(SESSION_EPOCH - SESSIONS_NEWEST_FIRST.index(session) * SESSION_STEP)


def agent_stamp(agent: str) -> str:
    """The newest stamp `make_transcripts` gave any file of one subagent.

    Two files carry one subagent -- its metadata and its own transcript --
    and the later of them is when it was last heard from.
    """

    names = fixture_agent_files()
    newest = max(
        index
        for index, name in enumerate(names)
        if name.rsplit("/", 1)[-1].startswith(agent + ".")
    )
    return utc_stamp(AGENT_EPOCH + newest * AGENT_STEP)


def ticket_paths(discovery: dict) -> list:
    return [ticket["path"] for run in discovery["runs"] for ticket in run["tickets"]]


def relative_ticket_paths(discovery: dict) -> list:
    """The same tickets named against the sink they were found in, so two
    sinks holding one corpus compare equal wherever either one sits."""

    root = discovery["root"]
    return [Path(path).relative_to(root).as_posix() for path in ticket_paths(discovery)]


def fixture_ticket_count() -> int:
    """Derived from the corpus on disk, so adding a fixture never silently
    weakens a count that exists to keep a test non-vacuous."""

    return sum(len(list((FIXTURES / run).glob("*.md"))) for run in FIXTURE_RUNS)


