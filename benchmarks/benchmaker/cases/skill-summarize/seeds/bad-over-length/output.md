# Cache rollout digest

The rollout log for 2026-03-02 records that the read-through cache was
enabled for 5% of traffic at 09:10 UTC and then for 100% of traffic at
14:40 UTC the same day, a staged enablement covering roughly five and a
half hours [S1].
The latency dashboard export compares the week before the rollout with
the day after full enablement and shows p99 read latency falling from
412 ms to 96 ms across that boundary [S2].
The incident 4471 write-up records that a stale-key bug served outdated
prices to 0.3% of sessions for 26 minutes on the day of the rollout,
and that the condition ended only when an engineer flushed the cache by
hand rather than through an automatic eviction path [S3].
The March cost report separates the two sides of the bill and shows
cache hosts adding $1,840 to the monthly total while origin database
spend fell $5,200 in the same month, leaving the month net cheaper by
$3,360 on those two lines alone [S4].
The on-call retrospective of 2026-03-05 records that no dashboard
tracked stale-key age, names that absence as the reason incident 4471
ran for 26 minutes before anyone noticed it, and files the missing
dashboard as the single open follow-up from the rollout [S5].
Read together, the rollout log and the latency export describe a
successful enablement, the incident write-up and the retrospective
describe its one unmonitored edge, and the cost report describes a
month that came out ahead despite the incident [S1] [S2] [S3] [S4] [S5].
