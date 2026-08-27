"""The instruction ceiling: what it counts, and where the words are.

The count and the refusal that prints it, in one place because they are one
fact. The grader already adds the parts up; printing only the sum charged a
cutter two blind recut round-trips per over-ceiling ticket -- the refusal
said the ticket was too long and never which section was long, so the next
cut guessed, and a guess that trims the wrong section arrives over the
ceiling again.

Held apart from `tickets_format` so the lint twin can consume the same
arithmetic without importing the ticket format wholesale, and so neither
holder grows a second counter that could disagree with this one. Imports
reach `tickets_markdown` directly: `tickets_format` re-exports what is
here, and a module this one imported back would close a cycle.
"""

from __future__ import annotations
import re
if __package__:
    from .tickets_markdown import _sections
else:
    from tickets_markdown import _sections
INSTRUCTION_BUDGET = 300
INSTRUCTION_SECTIONS = ('Goal', 'Context', 'Suggested files')
LINK_TARGET_RE = re.compile('\\]\\([^)]*\\)')
CEILING_RULE = 'rules/token-economy.md, section 11'


def _words(part: str) -> int:
    """One part in words, markdown link targets stripped."""
    return len(LINK_TARGET_RE.sub(']', str(part)).split())


def instruction_breakdown(text: str) -> tuple:
    """Each graded part with its own word count, largest first.

    The three author-facing semantic fields a child loads on dispatch.

    Largest first because the order is the advice: the part printed first
    is the one whose trimming moves the total most, which is the question a
    cutter over the ceiling actually has. Ties keep the canonical order,
    `sorted` being stable, so one ticket always renders one way.
    """
    sections = _sections(text)
    parts = [(name, _words(sections.get(name, ''))) for name in INSTRUCTION_SECTIONS]
    return tuple(sorted(parts, key=lambda part: -part[1]))


def instruction_words(text: str) -> int:
    """One ticket's instruction in words: the breakdown, added up."""
    return sum(count for _, count in instruction_breakdown(text))


def ceiling_arithmetic(text: str) -> str:
    """The sum the ceiling grades, written out part by part."""
    parts = instruction_breakdown(text)
    return ' + '.join(f'{name} {count}' for name, count in parts) + \
        f' = {sum(count for _, count in parts)}'


def ceiling_sentence(subject: str, text: str, budget: int = INSTRUCTION_BUDGET):
    """The refusal an over-ceiling instruction gets, or ``None``.

    Grades nothing about who is exempt: a caller decides whether this text
    is graded at all, and asks here only what the words come to.
    """
    count = instruction_words(text)
    if count <= budget:
        return None
    return (f'{subject} has a {count}-word instruction, {count - budget} over the '
            f'{budget}-word ceiling ({CEILING_RULE}): {ceiling_arithmetic(text)}, '
            'Cut the part named first: a compound goal is two items, not one '
            'longer ticket')
