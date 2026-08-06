# Cache rollout digest

The read-through cache reached full traffic at 14:40 UTC on 2026-03-02 [S1].
p99 read latency fell from 412 ms to 96 ms after full enablement [S2].
A stale-key bug served outdated prices to 0.3% of sessions for 26 minutes [S3].
The rollback runbook was followed exactly as written during the flush [S7].
Cache hosts added $1,840 per month while origin database spend fell $5,200 [S4].
Customer refunds for the affected sessions closed within a week [S9].
