"""Transcript parsing, caching, and session model."""

from __future__ import annotations

from reader.scripts.ui_model import *
from reader.scripts.ui_model import _facade_value, _in_tree, _json_object

def _make_room(cache: dict, limit: int):
    """Evict oldest-first until one insertion fits under ``limit``.

    Insertion-ordered and bounded, because the process outlives every run
    and every session it is ever asked about. A cache already below its
    limit evicts nothing: a negative slice here would drop the *newest*
    entries instead, which is the opposite of the policy.
    """

    excess = len(cache) - limit + 1
    for stale in list(cache)[:excess] if excess > 0 else ():
        cache.pop(stale, None)


DEFAULT_TRANSCRIPTS = (".claude", "projects")
SUBAGENTS_DIR = "subagents"
# Two files carry one subagent: its metadata, which is read, and its own
# conversation, which is only ever stat'd. Both are listed, because the
# later of the two mtimes is when the subagent was last heard from.
AGENT_FILE_GLOB = "agent-*"
AGENT_META_SUFFIX = ".meta.json"

RECORD_TYPE_KEY = "type"
AI_TITLE_RECORD = "ai-title"
AI_TITLE_KEY = "aiTitle"
WORKTREE_RECORD = "worktree-state"
# Observed on a live host: the worktree fields sit one level down under
# ``worktreeSession``, though the spec's evidence records them flat. Both
# shapes are read, because neither is anybody's contract.
WORKTREE_SESSION_KEY = "worktreeSession"
# ``worktreePath`` first: a session inside a linked worktree runs there, and
# that is the path the project directory name encodes.
WORKTREE_CWD_KEYS = ("worktreePath", "originalCwd")

# The one piece of evidence in the tree that a subagent ever ran. Observed
# on a live host over 305 subagents, and nobody's contract: an `assistant`
# record carries a `tool_use` block named `Agent` whose `id` is the
# subagent's `toolUseId`, and a later `user` record carries a `tool_result`
# block quoting that same id back once it has returned. Nothing else says
# it -- `tool-results/` names no subagent's id at all.
MESSAGE_KEY = "message"
CONTENT_KEY = "content"
TOOL_USE_BLOCK = "tool_use"
TOOL_RESULT_BLOCK = "tool_result"
TOOL_USE_ID_KEY = "tool_use_id"
BLOCK_ID_KEY = "id"
BLOCK_NAME_KEY = "name"
AGENT_TOOL_NAME = "Agent"

DIAGNOSTIC_UNREADABLE_TRANSCRIPT = "transcript could not be read"
DIAGNOSTIC_UNREADABLE_LINES = "unreadable transcript lines"
DIAGNOSTIC_NO_RECORDS = "transcript holds no records"
DIAGNOSTIC_UNDECODABLE_SLUG = "project directory name is not an encoded path"
DIAGNOSTIC_UNRENDERABLE_STAMP = "last activity time is outside the calendar"
# A row is a promise that the link on it opens. `/session` takes its id in a
# query string and `_safe_name` is the boundary that query crosses, so a
# filename the walk finds and the boundary refuses is named here instead of
# being listed under a link that answers "no such session" about a file this
# very page just drew.
DIAGNOSTIC_UNADDRESSABLE_SESSION = "session file cannot be addressed by name"

# Where a working directory came from, said on the page. The two are not
# equally trustworthy and the difference is not the reader's to hide.
CWD_FROM_RECORD = "from worktree-state"
CWD_FROM_NAME = "decoded from the directory name"

# The row, named once. Widening it is how the content wall gets breached, so
# it is a constant a test can hold rather than a shape spread over a format
# string.
SESSION_COLUMNS = ("sid", "title", "cwd", "when", "size", "agents", "notes")
SESSION_HEADINGS = (
    "session",
    "title",
    "working directory",
    "last activity",
    "bytes",
    "subagents",
    "notes",
)

# The subagent metadata this reader draws, named once for the same reason
# as SESSION_COLUMNS. `parentAgentId` is read and is deliberately not here:
# what it resolves to is drawn as an edge between two nodes already on the
# page, so the field's own value never reaches a reader.
AGENT_TYPE_KEY = "agentType"
AGENT_DESCRIPTION_KEY = "description"
AGENT_TOOL_USE_KEY = "toolUseId"
AGENT_DEPTH_KEY = "spawnDepth"
AGENT_PARENT_KEY = "parentAgentId"

AGENT_COLUMNS = ("agent", "type", "description", "depth", "state", "attached", "when")
AGENT_HEADINGS = (
    "subagent",
    "agent type",
    "description",
    "spawn depth",
    "activity",
    "attached to",
    "last activity",
)

DIAGNOSTIC_UNREADABLE_AGENT = "subagent metadata could not be read"
DIAGNOSTIC_INFERRED_EDGE = (
    "a dashed edge is inferred: the subagent records no parent, so it is "
    "drawn on the orchestrator by its spawn depth alone"
)
# The second guess, which is not the first one. Saying "records no parent"
# of a subagent that recorded one would be a false statement about another
# program's data, and it is the reader who would go looking for the parent
# that was supposedly never written down. No clause about spawn depth here
# either: a depth-3 record drawn on the orchestrator is not drawn by its
# depth, and a sentence claiming so contradicts the number beside it.
DIAGNOSTIC_UNRESOLVED_PARENT = (
    "a dashed edge is inferred: the subagent records a parent that names no "
    "other subagent of this session, so it is drawn on the orchestrator"
)

# The flowchart's own node, which is the session itself. Every subagent
# node is named for a file matching ``agent-*``, so no metadata file can
# collide with it.
ORCHESTRATOR_NODE = "orchestrator"
ORCHESTRATOR_ANCHOR = "session"

# What an edge was read off, said on the row it belongs to. A subagent at
# depth 1 was spawned by the session and nothing else could have spawned
# it; a recorded parent that resolves to a node on this page is a fact; a
# depth-2 subagent that records no parent is neither, and the guess is
# labelled a guess.
EDGE_FROM_DEPTH = "spawn depth 1"
EDGE_FROM_PARENT = "recorded parent"
EDGE_INFERRED = "inferred: no parent recorded"
# A fourth case, and the one the other three are not: a pointer was
# written down and resolved to nothing on this page. One sentence covers
# every shape that reaches here -- a stranger, the agent itself, and the
# orchestrator, which `agent_ids` deliberately withholds.
EDGE_PARENT_UNRESOLVED = (
    "inferred: recorded parent names no other subagent of this session"
)

# What the state was read off, said beside it. A state whose evidence is
# not on the page is indistinguishable from a guess.
EVIDENCE_CALLED = "called, no result yet"
EVIDENCE_RETURNED = "result recorded"
EVIDENCE_NONE = "no call in this transcript"


def transcript_root(value=None) -> Path:
    """The transcript root: ``value`` when given, else ``~/.claude/projects``.

    Path arithmetic and nothing else -- the tree is never opened here. This
    is also the only place the default is resolved, and ``main`` is its only
    caller, so a reader handed no root renders a named empty state instead
    of falling back to the operator's real transcripts.
    """

    if value:
        return Path(value).expanduser()
    return Path.home().joinpath(*DEFAULT_TRANSCRIPTS)


def decode_slug(slug) -> str:
    """A project directory name as the working directory it encodes, or ``""``.

    Claude Code names the directory after the working directory with every
    separator replaced by ``-``, which is not invertible: ``.`` encodes to
    ``-`` as well, and a ``-`` already in a directory name is
    indistinguishable from either, so ``…-orchflows--claude-worktrees-a-b``
    decodes wrong in three places. What comes back is a guess, named as one
    wherever it is the only source; a name that does not even open with the
    separator marker is refused rather than guessed at.
    """

    if not isinstance(slug, str) or not slug.startswith("-"):
        return ""
    return "/" + slug[1:].replace("-", "/")


def _stat_identity(path: Path):
    """``(name, size, mtime)`` for one file, or ``None`` when the path layer
    will not answer. The parse cache's key and the validator's contribution
    are these same three facts, so the page and the tag it is served under
    cannot disagree about which file they saw."""

    try:
        stat = path.stat()
    except OSError:
        return None
    return (str(path), stat.st_size, stat.st_mtime_ns)


def _worktree_cwd(record: dict) -> str:
    """The working directory one ``worktree-state`` record states, or ``""``."""

    nested = record.get(WORKTREE_SESSION_KEY)
    holders = (nested, record) if isinstance(nested, dict) else (record,)
    for holder in holders:
        for key in WORKTREE_CWD_KEYS:
            value = holder.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def _content_blocks(record: dict) -> list:
    """The content blocks of one conversation record, or none.

    Observed shape: the blocks sit under ``message.content``. The record is
    another program's JSON, so anything else there is not a block list.
    """

    message = record.get(MESSAGE_KEY)
    blocks = message.get(CONTENT_KEY) if isinstance(message, dict) else None
    if not isinstance(blocks, list):
        return []
    return [block for block in blocks if isinstance(block, dict)]


def _agent_evidence(record: dict, calls: set, returns: set) -> None:
    """Fold one record into the call and return sets.

    The tool *name* is the discriminator and dropping it is the whole bug
    this guards: a subagent's ``toolUseId`` is a tool-use id like any other,
    and a finished ``Bash`` command under that id is not a finished
    subagent. A return is only counted for a call already seen, which is
    also the order a transcript writes them in.
    """

    for block in _content_blocks(record):
        kind = block.get(RECORD_TYPE_KEY)
        if kind == TOOL_USE_BLOCK and block.get(BLOCK_NAME_KEY) == AGENT_TOOL_NAME:
            identifier = block.get(BLOCK_ID_KEY)
            if isinstance(identifier, str) and identifier:
                calls.add(identifier)
        elif kind == TOOL_RESULT_BLOCK:
            identifier = block.get(TOOL_USE_ID_KEY)
            if identifier in calls:
                returns.add(identifier)


def _transcript_summary(path: Path) -> dict:
    """The two labels the index draws from one transcript, the evidence that
    each subagent ever ran, and nothing else.

    Streamed a line at a time, and every line that is not one of the
    rendered record types is dropped before a single value is taken from it.
    A real transcript is megabytes of conversation; none of it is ever held
    long enough to be filtered later, and what survives this pass is a
    handful of tool-use ids -- one per subagent the session spawned.
    """

    calls, returns = set(), set()
    summary = {
        "title": "",
        "cwd": "",
        "records": 0,
        "skipped": 0,
        "unreadable": False,
        "agent_calls": calls,
        "agent_returns": returns,
    }
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if not line.strip():
                    continue
                record = _json_object(line)
                if record is None:
                    summary["skipped"] += 1
                    continue
                summary["records"] += 1
                kind = record.get(RECORD_TYPE_KEY)
                if kind == AI_TITLE_RECORD:
                    title = record.get(AI_TITLE_KEY)
                    # Last one wins: the title is rewritten as the session
                    # goes on, and the reader wants the current one.
                    if isinstance(title, str) and title.strip():
                        summary["title"] = title.strip()
                elif kind == WORKTREE_RECORD:
                    cwd = _worktree_cwd(record)
                    if cwd:
                        summary["cwd"] = cwd
                else:
                    _agent_evidence(record, calls, returns)
    except OSError:
        # Unreadable, or gone between the listing and the open. Whatever was
        # read before that stands; the absence is named, not guessed at.
        summary["unreadable"] = True
    return summary


TRANSCRIPT_CACHE = {}
TRANSCRIPT_CACHE_LIMIT = 256


def cached_transcript(path: Path, identity) -> dict:
    """``_transcript_summary`` memoized on the file's stat identity.

    The index draws one title and one working directory out of a file that
    is routinely megabytes, for every session on the machine, and the poll
    asks for the page every second. Keyed on name, size and mtime -- the
    same three facts the page's own validator is built from -- so an
    unchanged transcript is parsed once and a changed one is parsed again.
    """

    summary = TRANSCRIPT_CACHE.get(identity)
    if summary is None:
        summary = _facade_value("_transcript_summary", _transcript_summary)(path)
        _make_room(TRANSCRIPT_CACHE, TRANSCRIPT_CACHE_LIMIT)
        TRANSCRIPT_CACHE[identity] = summary
    return summary


def _subagent_files(path: Path) -> tuple:
    """Every subagent file beside one transcript, metadata and conversation
    alike.

    The conversation is listed and never opened: it is megabytes of the
    same content the transcript holds, and the only thing read off it is
    the mtime the flowchart draws as a last activity. A session directory
    that does not exist is no subagents, not an error -- most sessions
    spawn nothing.
    """

    directory = _in_tree(path.parent, path.stem, SUBAGENTS_DIR)
    if directory is None:
        return ()
    try:
        entries = sorted(directory.glob(AGENT_FILE_GLOB)) if directory.is_dir() else ()
        resolved = (_in_tree(directory, entry.name) for entry in entries)
        return tuple(path for path in resolved if path is not None and path.is_file())
    except OSError:
        return ()


def _agent_id(path: Path) -> str:
    """The subagent one of its files is named for: ``agent-aa11.meta.json``
    and ``agent-aa11.jsonl`` are two files about one subagent."""

    for suffix in (AGENT_META_SUFFIX, JSONL_SUFFIX):
        if path.name.endswith(suffix):
            return path.name[: -len(suffix)]
    return path.name


def _subagent_identities(files) -> tuple:
    """The stat identity of every subagent file beside one transcript.

    This is the validator's contribution for the subagent tree, so it
    covers what the pages read: the metadata they parse and the mtime they
    draw. A narrower basis would answer 304 to a flowchart that has moved.
    """

    return tuple(
        identity
        for identity in (_facade_value("_stat_identity", _stat_identity)(file) for file in files)
        if identity is not None
    )


def _agent_count(files) -> int:
    """How many subagents one session spawned: one per metadata file, not
    one per file."""

    return sum(1 for file in files if file.name.endswith(AGENT_META_SUFFIX))


def _agent_text(value) -> str:
    """One metadata string field, or ``""``. Another program's undocumented
    JSON can hold anything at any key, so a value of the wrong type is an
    absence rather than something to render."""

    return value.strip() if isinstance(value, str) and value.strip() else ""


def _agent_depth(value):
    """``spawnDepth`` as an integer, or ``None``. ``True`` is an ``int`` in
    Python and is not a depth."""

    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _agent_record(meta: Path, modified) -> dict:
    """The named metadata fields of one subagent, each degrading to an
    absence rather than to a traceback. ``modified`` is the newest mtime of
    the subagent's files, or ``None`` when the path layer would describe
    none of them -- not 0, which ``_stamp`` would draw as the epoch."""

    record = {
        "id": _agent_id(meta),
        "type": "",
        "description": "",
        "tool_use_id": "",
        "depth": None,
        "parent": "",
        "modified": modified,
        "unreadable": False,
    }
    try:
        parsed = _json_object(meta.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        parsed = None
    if parsed is None:
        record["unreadable"] = True
        return record
    record["type"] = _agent_text(parsed.get(AGENT_TYPE_KEY))
    record["description"] = _agent_text(parsed.get(AGENT_DESCRIPTION_KEY))
    record["tool_use_id"] = _agent_text(parsed.get(AGENT_TOOL_USE_KEY))
    record["depth"] = _agent_depth(parsed.get(AGENT_DEPTH_KEY))
    record["parent"] = _agent_text(parsed.get(AGENT_PARENT_KEY))
    return record


def read_agents(path: Path) -> list:
    """Every subagent recorded beside one transcript, in the tree's order.

    A metadata file is a few hundred bytes and a session has a few dozen of
    them, so this is the one place the detail view reads that the index
    does not. Its cost is a directory listing plus one small read per
    subagent -- no transcript is opened here at all.
    """

    activity = {}
    metas = []
    for file in _subagent_files(path):
        identity = _facade_value("_stat_identity", _stat_identity)(file)
        if identity is not None:
            agent = _agent_id(file)
            activity[agent] = max(activity.get(agent, 0), identity[2])
        if file.name.endswith(AGENT_META_SUFFIX):
            metas.append(file)
    return [_agent_record(meta, activity.get(_agent_id(meta))) for meta in metas]


def _session_diagnostics(summary: dict) -> list:
    """What one transcript could not be read to say."""

    diagnostics = []
    if summary["unreadable"]:
        diagnostics.append(DIAGNOSTIC_UNREADABLE_TRANSCRIPT)
    if summary["skipped"]:
        diagnostics.append(
            "{0}: {1}".format(DIAGNOSTIC_UNREADABLE_LINES, summary["skipped"])
        )
    # An empty transcript and a healthy one must not look alike: a layout
    # change that stopped every line parsing would otherwise render a page
    # of blanks that reads as "nothing happened here".
    if not summary["records"] and not summary["unreadable"]:
        diagnostics.append(DIAGNOSTIC_NO_RECORDS)
    return diagnostics


def _label_session(session: dict) -> dict:
    """One session's labels, from the cached parse of its own transcript.
    Returns the summary, so a caller that needs more than the labels does
    not parse the file a second time."""

    summary = cached_transcript(session["path"], session["identity"])
    session["title"] = summary["title"]
    session["cwd"] = summary["cwd"] or session["named_cwd"]
    if summary["cwd"]:
        session["cwd_source"] = CWD_FROM_RECORD
    else:
        session["cwd_source"] = CWD_FROM_NAME if session["named_cwd"] else ""
    session["diagnostics"] = _session_diagnostics(summary)
    return summary


def _agent_activity(agent: dict, summary: dict) -> tuple:
    """``(state, what it was read off)`` for one subagent.

    Ordered by strength of evidence, and it runs out fast: a result quoting
    the call is the only thing that says finished, an unanswered call is the
    only thing that says running, and everything else is `unknown`. Nothing
    here has a default branch that claims a state -- the absence of evidence
    is the third state, not a reason to pick one of the other two.
    """

    called = agent["tool_use_id"]
    if called and called in summary["agent_returns"]:
        return ACTIVITY_FINISHED, EVIDENCE_RETURNED
    if called and called in summary["agent_calls"]:
        return ACTIVITY_RUNNING, EVIDENCE_CALLED
    return ACTIVITY_UNKNOWN, EVIDENCE_NONE


def read_session(session: dict) -> dict:
    """One session, labelled, with every subagent recorded beside it and
    each subagent's activity read off the session's own transcript.

    The parse is the one ``_label_session`` already made and cached, so the
    states cost no second pass over the file.
    """

    summary = _label_session(session)
    session["agents"] = read_agents(session["path"])
    for agent in session["agents"]:
        agent["state"], agent["evidence"] = _agent_activity(agent, summary)
    return session
