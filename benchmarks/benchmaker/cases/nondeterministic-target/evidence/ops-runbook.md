# Runbook — shard assignment

## Replaying an incident

Every request log line carries the seed the picker ran with. To
reproduce an assignment, rerun `sampler.py` with that seed and the
same draw count and compare the stream line for line. A replay that
does not reproduce the recorded stream is an incident in itself: the
picker is reading entropy it should not read, and no request trace can
be trusted afterwards.

## Capacity audit

Monthly we draw 20,000 assignments under one pinned seed and check
each shard's share against its weight. The accepted tolerance is 1.5
percentage points — shard 0 must land between 5,700 and 6,300 of
20,000. Two consecutive audits outside the band open a ticket against
the picker, not against capacity.

The audit is run under a pinned seed on purpose: an audit whose own
verdict changes run to run cannot tell a rebalance from noise.

## What we have been bitten by

A picker that is reproducible and correctly weighted can still be
wrong: if the stream for a given seed changes, every archived trace
silently stops replaying, and nothing in the aggregate numbers moves.
Check the stream, not just the histogram.
