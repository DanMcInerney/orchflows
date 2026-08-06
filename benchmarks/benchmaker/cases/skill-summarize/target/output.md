# Cache rollout digest

The read-through cache reached 5% of traffic at 09:10 UTC and full traffic at 14:40 UTC on 2026-03-02 [S1].
p99 read latency fell from 412 ms to 96 ms after full enablement [S2].
A stale-key bug served outdated prices to 0.3% of sessions for 26 minutes before the cache was flushed [S3].
Detection was slow because no dashboard tracked stale-key age [S5].
Cache hosts added $1,840 per month while origin database spend fell $5,200 [S4].
The rollout cut latency and net cost and left one open follow-up [S2] [S4] [S5].
