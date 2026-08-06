# Source set — cache rollout review

Five sources, ids `S1`–`S5`. A summary of this set may cite these ids
and no others; there is no `S6`.

## S1 — rollout log, 2026-03-02

The read-through cache reached 5% of traffic at 09:10 UTC and 100% of
traffic at 14:40 UTC on 2026-03-02.

## S2 — latency dashboard export

p99 read latency fell from 412 ms in the week before the rollout to
96 ms in the day after full enablement.

## S3 — incident 4471 write-up

A stale-key bug served outdated prices to 0.3% of sessions for 26
minutes on 2026-03-02 before the cache was flushed by hand.

## S4 — cost report, March 2026

Cache hosts added $1,840 to the monthly bill; origin database spend
fell $5,200 in the same month.

## S5 — on-call retrospective, 2026-03-05

No dashboard tracked stale-key age, which is why incident 4471 ran 26
minutes before anyone noticed. The team filed the dashboard as the one
open follow-up.
