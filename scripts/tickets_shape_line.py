"""The one line a driver writes down before its first dispatch.

A frame's shape is the wave plan stated once, in the open, before anything
is minted: `outline > [do, do] > judge` says three waves, two of them
parallel, and a reader who arrives at the ticket tree later can tell what
the driver meant to do from what it actually did. The grammar itself is
owned by `docs/vocabulary.md`'s `routing shape` entry; this module is the
only place it is *parsed*, and the refusals below are the only place its
notation is spelled back at a caller who got it wrong.

Two names are refused rather than parsed, because both are lawful English
and neither is a frame. `do` alone is the worker lane -- one ticket, no
wave plan, nothing to journal -- and `direct` is the lane that opens no
frame at all. A driver that writes either has picked the wrong command,
not written a bad shape, so the refusal says which command it wanted.

The parser reports the first token that does not belong where it stands
rather than "unparseable": a shape line is short and hand-written, and the
one thing its author cannot derive from a rejection is *where* it went
wrong.
"""

from __future__ import annotations

import re

# The reserved names, and what they bind. Free identifiers are the driver's
# own labels for a wave; these three name kernel verbs, so a reader knows
# a wave called `judge` is a judge without asking.
RESERVED_NAMES = ("do", "outline", "judge")
# The notation the parser recognises as structure rather than as a name.
# Public because it is half the anchor set a check reads to hold the owner
# prose and the echo below to one grammar; `_parse_item` reads it as the
# "not a name" test.
GRAMMAR_TOKENS = (">", "[", "]", ",", "*")
SHAPE_RECORD_ID = "shape"
SHAPE_PREFIX = "shape:"
SHAPE_USAGE = '--shape "<line>"'
WORKFLOW_SHAPE_PREFIX = "workflow:"

# One line, and a pointer at the owner rather than a second definition:
# `docs/vocabulary.md`'s `routing shape` entry states what these mean.
SHAPE_GRAMMAR = (
    "shape grammar: `a > b` waves in order, `[a, b]` one wave in parallel, "
    "`a[*]` a count an outline decides, names free except the reserved "
    "`do`, `outline`, `judge` (docs/vocabulary.md, `routing shape`)"
)

_NAME = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]*")
_END = "<end of line>"


def missing_shape_refusal() -> dict:
    """What a root frame minted with neither `--shape` nor `--workflow` gets.

    Before any write: a frame whose plan was never stated is the failure
    the shape line exists to end, and minting one and then complaining
    would leave the unplanned frame behind as the record.
    """

    return {"error": (
        f"a root frame states its wave plan at open: pass {SHAPE_USAGE}, or "
        "--workflow NAME when a saved workflow's body is the plan. "
        + SHAPE_GRAMMAR
    )}


def shape_for(shape, workflow, parent):
    """`(shape, refusal)`: the wave plan one `frame-open` opens under.

    An explicit `--shape` outranks `--workflow`, because a driver that
    wrote the line meant the line. A saved workflow's body *is* its plan,
    so its name stands in for one. Only a root owes one at all: a called
    frame is already a wave of its caller's shape, and demanding it restate
    the plan would put the same fact in two places.
    """

    if shape is not None:
        return parse_shape(shape)
    if workflow:
        return workflow_shape(workflow), None
    if not parent:
        return None, missing_shape_refusal()
    return None, None


def workflow_shape(workflow: str) -> str:
    """The shape a saved workflow's name stands for.

    Not grammar and never parsed as it: the workflow's own body is the wave
    plan, and this records which body to go read.
    """

    return f"{WORKFLOW_SHAPE_PREFIX}{workflow}"


def shape_record(shape: str) -> str:
    """The journal line `frame-open` files and `frame-close` reads back."""

    return f"{SHAPE_PREFIX} {shape}"


def journal_shape(journal) -> str:
    """The shape one frame's journal recorded, or ''.

    A prefix match on one line, the way `unjudged_reason` reads its own
    line: the first `shape:` wins, so a later wave that quotes the shape
    while discussing it cannot displace the record `frame-open` filed.
    """

    for line in str(journal or "").splitlines():
        text = line.strip()
        if text.startswith(SHAPE_PREFIX):
            recorded = text[len(SHAPE_PREFIX):].strip()
            if recorded:
                return recorded
    return ""


def parse_shape(text):
    """`(shape, refusal)` for one `--shape` line.

    The shape returned is the caller's own line, stripped: it is prose a
    person wrote and a person reads back, and normalising its spacing would
    only make the journal disagree with the command that filed it.
    """

    line = (text or "").strip()
    if not line or "\n" in line:
        return None, {"error": (
            f"--shape takes one non-empty line. {SHAPE_GRAMMAR}"
        )}
    if line == "do":
        return None, {"error": (
            "one ticket is the worker lane: run tickets.py do"
        )}
    if line == "direct":
        return None, {"error": (
            "direct opens no frame: the direct lane makes the change in this "
            "session and records it in the medium's own history"
        )}
    tokens, bad = _tokens(line)
    if bad is not None:
        return None, _bad_token(line, bad)
    bad = _parse(tokens)
    if bad is not None:
        return None, _bad_token(line, bad)
    return line, None


def _bad_token(line: str, token: str) -> dict:
    return {"error": (
        f"shape `{line}` does not parse at `{token}`. {SHAPE_GRAMMAR}"
    )}


def _tokens(line: str):
    """`(tokens, bad)`: the line's tokens, or the first character that is none."""

    tokens = []
    index = 0
    while index < len(line):
        character = line[index]
        if character.isspace():
            index += 1
            continue
        if character in GRAMMAR_TOKENS:
            tokens.append(character)
            index += 1
            continue
        match = _NAME.match(line, index)
        if match is None:
            return None, character
        tokens.append(match.group())
        index = match.end()
    return tokens, None


def _parse(tokens):
    """The first token that does not belong where it stands, or ``None``."""

    position = 0
    while True:
        position, bad = _parse_wave(tokens, position)
        if bad is not None:
            return bad
        if position == len(tokens):
            return None
        if tokens[position] != ">":
            return tokens[position]
        position += 1
        if position == len(tokens):
            return ">"


def _parse_wave(tokens, position):
    """One wave: a single item, or `[` items separated by `,` `]`."""

    if position >= len(tokens):
        return position, _END
    if tokens[position] != "[":
        return _parse_item(tokens, position)
    position += 1
    while True:
        position, bad = _parse_item(tokens, position)
        if bad is not None:
            return position, bad
        if position >= len(tokens):
            return position, _END
        if tokens[position] == "]":
            return position + 1, None
        if tokens[position] != ",":
            return position, tokens[position]
        position += 1


def _parse_item(tokens, position):
    """One name, optionally carrying the outline-decided count `[*]`."""

    if position >= len(tokens):
        return position, _END
    if tokens[position] in GRAMMAR_TOKENS:
        return position, tokens[position]
    position += 1
    if position >= len(tokens) or tokens[position] != "[":
        return position, None
    if tokens[position + 1:position + 3] == ["*", "]"]:
        return position + 3, None
    following = tokens[position + 1:position + 2]
    return position, following[0] if following else "["


__all__ = (
    "GRAMMAR_TOKENS", "RESERVED_NAMES", "SHAPE_GRAMMAR", "SHAPE_PREFIX",
    "SHAPE_RECORD_ID", "SHAPE_USAGE", "WORKFLOW_SHAPE_PREFIX", "journal_shape",
    "missing_shape_refusal", "parse_shape", "shape_for", "shape_record",
    "workflow_shape",
)
