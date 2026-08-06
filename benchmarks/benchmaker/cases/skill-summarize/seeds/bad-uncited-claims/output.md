# Cache rollout digest

The read-through cache reached full traffic at 14:40 UTC on 2026-03-02 [S1].
p99 read latency fell from 412 ms to 96 ms after full enablement [S2].
The rollout was on the whole the smoothest of the quarter.
A stale-key bug served outdated prices to 0.3% of sessions for 26 minutes [S3].
Nobody had a dashboard for stale-key age, so it ran long.
Cache hosts added $1,840 per month while origin database spend fell $5,200 [S4].
