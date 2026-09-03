"""Leaks beside the tree: seven places a public client credential could hide.

Each takes the artifact the run really produced and puts one secret in one
field of it, so a rejection is attributable to that field and the run under
test was not touched. A scan that only knew the fields somebody thought of
would pass most of these, which is why the one it is holding is exhaustive
over whatever an emitted value happens to hold.

`in_a_record_locator` is the one drawn from life. A query-placed credential
goes onto the url at send time, and the address the origin answers from is
that url with the key still on it — so a record that publishes where it was
answered from is the one string in this package that can carry a `K1` secret
out of the transport seam.

Nothing in the package imports this file and no discovery pattern matches it.
"""

from __future__ import annotations

from dataclasses import replace


def _with_first_record(artifact, **changes):
    first = replace(artifact.records[0], **changes)
    return replace(artifact, records=(first,) + artifact.records[1:])


def in_a_record_attribute(artifact, secret):
    """Under one of the route's own attribute names, three levels down."""

    return _with_first_record(
        artifact, attributes=artifact.records[0].attributes + (("final_url", secret),)
    )


def in_a_record_locator(artifact, secret):
    """On the address the record says it came from, where a query key rides."""

    record = artifact.records[0]
    return _with_first_record(
        artifact, canonical_locator=record.canonical_locator + "?key=" + secret
    )


def in_a_record_body(artifact, secret):
    """Inside the text of the row, which is the largest string a record holds."""

    record = artifact.records[0]
    return _with_first_record(artifact, body=record.body + "\nsent with " + secret)


def in_a_step_loss(artifact, secret):
    """As a loss code, where a scan of the record families would never look."""

    first = replace(artifact.steps[0], loss=artifact.steps[0].loss + (secret,))
    return replace(artifact, steps=(first,) + artifact.steps[1:])


def in_the_artifact_loss(artifact, secret):
    """On the artifact itself, outside every record and every step."""

    return replace(artifact, loss=artifact.loss + (secret,))


def in_a_group_key(artifact, secret):
    """Inside a grouping key, which is a tuple of strings inside a tuple."""

    first = replace(artifact.groups[0], key=artifact.groups[0].key + (secret,))
    return replace(artifact, groups=(first,) + artifact.groups[1:])


def in_a_manifest_query(manifest, secret):
    """In the manifest, before any read happens — the caller's own copy."""

    first = replace(manifest.steps[0], query=manifest.steps[0].query + " " + secret)
    return replace(manifest, steps=(first,) + manifest.steps[1:])


def in_a_ledger_reason(ledger, secret):
    """On the stop marker, in the one field of the ledger that holds prose."""

    return ledger[:-1] + (replace(ledger[-1], reason=ledger[-1].reason + ": " + secret),)


ARTIFACT_LEAKS = (
    ("a record attribute", in_a_record_attribute),
    ("a record locator", in_a_record_locator),
    ("a record body", in_a_record_body),
    ("a step's loss", in_a_step_loss),
    ("the artifact's loss", in_the_artifact_loss),
    ("a group key", in_a_group_key),
)
