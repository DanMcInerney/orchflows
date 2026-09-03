"""A disposition renderer that calls any recorded success a current one.

Written beside the tree and never imported by the package. It is the shape row
2 exists to reject: a ledger entry is treated as evidence forever, so an
adapter last proven a year ago reports `verified` and nobody re-proves it. The
freshness window is read and then not applied, which is how this mistake looks
in real code — the arithmetic is there and its answer is discarded.
"""

from super_research import cli


def disposition_of(ledger, adapter_id, now, max_age_seconds=cli.SMOKE_MAX_AGE_SECONDS):
    last_success = ledger.get(adapter_id, "")
    if not last_success:
        return cli.Disposition(
            adapter_id=adapter_id,
            state=cli.UNVERIFIED,
            reason=cli.NEVER_SMOKED,
            last_success="",
        )
    cli.seconds_since(last_success, now)
    return cli.Disposition(
        adapter_id=adapter_id,
        state=cli.VERIFIED,
        reason=cli.FRESH_SUCCESS,
        last_success=last_success,
    )
